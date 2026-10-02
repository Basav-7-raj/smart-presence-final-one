import csv, io, json, os, time
from datetime import timedelta
from pathlib import Path
import cv2
import numpy as np
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .face_engine import detect_faces, extract_best_feature, compare_features, feature_from_json, extract_feature_from_face
from .models import PersonProfile, PresenceRecord, UnknownEvent, SystemEvent, SystemSetting

DEFAULTS = {'match_threshold':'0.363','liveness_threshold':'0.018','unknown_alert':'1','sound_alert':'1','auto_capture_unknown':'1','duplicate_window':'10','camera':'0','theme':'dark'}
_liveness_state = {}


def setting(key): return SystemSetting.objects.filter(key=key).values_list('value', flat=True).first() or DEFAULTS.get(key,'')
def set_setting(key, value): SystemSetting.objects.update_or_create(key=key, defaults={'value':str(value)})
def bootstrap_settings():
    for k,v in DEFAULTS.items(): SystemSetting.objects.get_or_create(key=k, defaults={'value':v})

def _client_key(request): return request.headers.get('X-Client-ID','browser-default')
def _liveness_check(client_id, face):
    now=time.monotonic(); pts=np.asarray(face['landmarks'],dtype=np.float32); scale=max(float(np.linalg.norm(pts[0]-pts[1])),1.0)
    geom=np.array([(pts[2,0]-pts[0,0])/scale,(pts[2,1]-(pts[0,1]+pts[1,1])/2)/scale,(pts[1,0]-pts[0,0])/scale],dtype=np.float32)
    state=_liveness_state.get(client_id); cur={'t':now,'geom':geom}
    if state is None or now-state['t']>4.0: _liveness_state[client_id]=cur; return False,'Move your head slightly for liveness verification.'
    delta=float(np.linalg.norm(geom-state['geom'])); _liveness_state[client_id]=cur
    ok=delta>=float(setting('liveness_threshold') or .018)
    return ok, 'Liveness verified' if ok else 'Move your head slightly for liveness verification.'

def _today(): return timezone.localdate()
def _present_people():
    cutoff=timezone.now()-timedelta(minutes=15); ids=PresenceRecord.objects.filter(timestamp__gte=cutoff).values_list('person_id',flat=True).distinct(); return PersonProfile.objects.filter(id__in=ids,active=True)
def _save_snapshot(frame):
    folder=Path(settings.MEDIA_ROOT)/'unknown_events'; folder.mkdir(parents=True,exist_ok=True); name=f'unknown_{timezone.now().strftime("%Y%m%d_%H%M%S_%f")}.jpg'; path=folder/name; cv2.imwrite(str(path),frame); return f'unknown_events/{name}'

def dashboard(request):
    bootstrap_settings(); return render(request,'tracker/dashboard.html',_context())
@login_required
def admin_panel(request): return render(request,'tracker/admin_panel.html',_context())
def _context():
    people=PersonProfile.objects.order_by('name'); today=_today(); records=PresenceRecord.objects.filter(timestamp__date=today).select_related('person'); unknowns=UnknownEvent.objects.all()[:20]
    return {'people':people,'records':records[:30],'unknowns':unknowns,'people_count':people.filter(active=True).count(),'present_count':_present_people().count(),'unknown_count':UnknownEvent.objects.filter(timestamp__date=today).count(),'event_count':SystemEvent.objects.filter(timestamp__date=today).count()}

@require_POST
@login_required
def register_face(request):
    name=request.POST.get('name','').strip(); student_id=request.POST.get('student_id','').strip(); image=request.FILES.get('image')
    if not name or not student_id or not image: return JsonResponse({'status':'error','message':'Name, Student ID and photo are required.'},status=400)
    try:
        frame=cv2.imdecode(np.frombuffer(image.read(),np.uint8),cv2.IMREAD_COLOR)
        if frame is None: raise ValueError('Invalid image file.')
        feature,face=extract_best_feature(frame)
        if feature is None: return JsonResponse({'status':'error','message':'No clear face found. Use a front-facing photo.'},status=400)
        person,_=PersonProfile.objects.get_or_create(student_id=student_id); person.name=name; person.active=True; person.set_encoding(feature); person.save()
        SystemEvent.objects.create(event_type='system',message=f'{name} registered',severity='INFO',person=person)
        return JsonResponse({'status':'success','message':f'{name} registered successfully.'})
    except Exception as exc: return JsonResponse({'status':'error','message':str(exc)},status=500)

@require_POST
@login_required
def toggle_person(request, pk):
    p=get_object_or_404(PersonProfile,pk=pk); p.active=not p.active; p.save(update_fields=['active','updated_at']); return JsonResponse({'status':'success','active':p.active})
@require_POST
@login_required
def delete_person(request, pk):
    p=get_object_or_404(PersonProfile,pk=pk); name=p.name; p.delete(); SystemEvent.objects.create(event_type='system',message=f'{name} removed',severity='INFO'); return JsonResponse({'status':'success'})

@require_POST
def recognize(request):
    try:
        frame=cv2.imdecode(np.frombuffer(request.body,np.uint8),cv2.IMREAD_COLOR)
        if frame is None: return JsonResponse({'status':'error','message':'Invalid frame.'},status=400)
        faces=detect_faces(frame); people=list(PersonProfile.objects.filter(active=True)); client=_client_key(request); results=[]; threshold=float(setting('match_threshold') or .363); snapshot_enabled=setting('auto_capture_unknown')=='1'
        for face in faces:
            raw=np.zeros((15,),dtype=np.float32); raw[:4]=face['bbox']; raw[4:14]=np.asarray(face['landmarks']).reshape(-1); raw[14]=face['score']; feature=extract_feature_from_face(frame,raw)
            best=None; score=-1
            for person in people:
                try:
                    s=compare_features(feature,feature_from_json(person.encoding_json))
                    if s>score: score=s; best=person
                except Exception: pass
            live_ok,live_msg=_liveness_check(client,face)
            verified=best is not None and score>=threshold and live_ok
            if verified:
                window=int(setting('duplicate_window') or 10); since=timezone.now()-timedelta(minutes=window)
                if not PresenceRecord.objects.filter(person=best,timestamp__gte=since).exists():
                    PresenceRecord.objects.create(person=best,confidence=float(score),liveness_passed=True)
                    SystemEvent.objects.create(event_type='verified',message=f'{best.name} verified',severity='INFO',person=best)
                results.append({'recognized':True,'name':best.name,'student_id':best.student_id,'score':round(float(score),3),'liveness':True,'bbox':face['bbox']})
            else:
                reason='Liveness verification required.' if best is not None and score>=threshold else 'Unknown person.'
                snap=_save_snapshot(frame) if snapshot_enabled else ''
                ev=UnknownEvent.objects.create(best_score=max(0,float(score)),liveness_passed=live_ok, snapshot=snap or None, severity='HIGH' if live_ok else 'MEDIUM', message=reason)
                SystemEvent.objects.create(event_type='liveness' if (best is not None and score>=threshold and not live_ok) else 'unknown',message=reason,severity=ev.severity)
                results.append({'recognized':False,'message':reason,'score':round(max(0,float(score)),3),'liveness':live_ok,'bbox':face['bbox'],'event_id':ev.id})
        return JsonResponse({'status':'success','recognized':any(x['recognized'] for x in results),'face_count':len(results),'results':results,'threshold':threshold,'fps_hint':0})
    except Exception as exc: return JsonResponse({'status':'error','message':str(exc)},status=500)

@require_GET
def events(request):
    qs=SystemEvent.objects.select_related('person')[:80]
    return JsonResponse({'events':[{'id':e.id,'type':e.event_type,'message':e.message,'severity':e.severity,'timestamp':e.timestamp.isoformat(),'person':e.person.name if e.person else None} for e in qs], 'present':[{'name':p.name,'student_id':p.student_id,'last_seen':PresenceRecord.objects.filter(person=p).first().timestamp.isoformat()} for p in _present_people()]})

@login_required
def people_page(request): return render(request,'tracker/people.html',{'people':PersonProfile.objects.order_by('name')})
@login_required
def events_page(request): return render(request,'tracker/events.html',{'events':SystemEvent.objects.select_related('person')[:150],'unknowns':UnknownEvent.objects.all()[:100]})
@login_required
def analytics(request):
    today=_today(); days=[]
    for i in range(6,-1,-1):
        d=today-timedelta(days=i); days.append({'date':d.strftime('%d %b'),'count':PresenceRecord.objects.filter(timestamp__date=d).values('person').distinct().count()})
    return render(request,'tracker/analytics.html',{'people':PersonProfile.objects.filter(active=True).count(),'present':PresenceRecord.objects.filter(timestamp__date=today).values('person').distinct().count(),'unknown':UnknownEvent.objects.filter(timestamp__date=today).count(),'days':json.dumps(days)})
@login_required
def privacy(request): return render(request,'tracker/privacy.html')
@login_required
def settings_page(request): return render(request,'tracker/settings.html',{'settings':{k:setting(k) for k in DEFAULTS}})
@login_required
@require_POST
def save_settings(request):
    for k in DEFAULTS:
        if k in request.POST: set_setting(k,request.POST[k])
    return JsonResponse({'status':'success'})
@login_required
@require_POST
def acknowledge(request,pk):
    e=get_object_or_404(UnknownEvent,pk=pk); e.acknowledged=True; e.save(update_fields=['acknowledged']); return JsonResponse({'status':'success'})
@login_required
def evidence(request): return render(request,'tracker/evidence.html',{'events':UnknownEvent.objects.all()[:150]})
@login_required
def report_csv(request):
    response=HttpResponse(content_type='text/csv'); response['Content-Disposition']=f'attachment; filename="smart_presence_{_today()}.csv"'; w=csv.writer(response); w.writerow(['Name','Student ID','First Seen','Events'])
    for p in PersonProfile.objects.order_by('name'):
        rows=PresenceRecord.objects.filter(person=p,timestamp__date=_today()); first=rows.order_by('timestamp').first(); w.writerow([p.name,p.student_id,timezone.localtime(first.timestamp).strftime('%I:%M %p') if first else '-',rows.count()])
    return response
@login_required
def report_pdf(request):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError: return HttpResponse('Install reportlab to enable PDF reports.',status=500)
    buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=A4); y=800; c.setFont('Helvetica-Bold',18); c.drawString(40,y,'SMART PRESENCE REPORT'); y-=28; c.setFont('Helvetica',10); c.drawString(40,y,f'Date: {_today()}'); y-=28
    for p in PersonProfile.objects.order_by('name'):
        rows=PresenceRecord.objects.filter(person=p,timestamp__date=_today()); first=rows.order_by('timestamp').first(); line=f'{p.name} | {p.student_id} | {timezone.localtime(first.timestamp).strftime("%I:%M %p") if first else "-"} | {rows.count()} events'; c.drawString(40,y,line[:105]); y-=16
        if y<50: c.showPage(); y=800
    c.save(); buf.seek(0); return HttpResponse(buf.getvalue(),content_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="smart_presence_{_today()}.pdf"'})
@login_required
@require_POST
def reset_demo(request):
    PresenceRecord.objects.all().delete(); UnknownEvent.objects.all().delete(); SystemEvent.objects.all().delete(); return JsonResponse({'status':'success','message':'Demo history reset. Registered people were kept.'})
