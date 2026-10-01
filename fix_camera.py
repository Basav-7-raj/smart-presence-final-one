from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
base = ROOT / 'tracker' / 'templates' / 'tracker' / 'base.html'
dash = ROOT / 'tracker' / 'templates' / 'tracker' / 'dashboard.html'

if not base.exists() or not dash.exists():
    raise SystemExit('ERROR: Extract SmartPresence_Final_Competition.zip first, then run this script from the project root.')

# Remove the stale script reference. The dashboard has its own inline JavaScript.
b = base.read_text(encoding='utf-8')
b = b.replace('<script src="/static/tracker/app.js"></script>', '')
base.write_text(b, encoding='utf-8')

d = dash.read_text(encoding='utf-8')

# Replace the broken scan() function with valid JavaScript.
start = d.find('async function scan(){')
end = d.find('\nfunction getCookie', start)
if start == -1 or end == -1:
    raise SystemExit('ERROR: Could not locate dashboard scan() function.')

scan = """async function scan(){
  if(!running || video.readyState < 2){ setTimeout(scan,850); return; }
  canvas.width=video.videoWidth;
  canvas.height=video.videoHeight;
  ctx.drawImage(video,0,0);
  canvas.toBlob(async b=>{
    if(!b) return;
    try{
      const res=await fetch('/recognize/',{
        method:'POST',
        headers:{
          'Content-Type':'image/jpeg',
          'X-Client-ID':client,
          'X-CSRFToken':getCookie('csrftoken')
        },
        body:b
      });
      const j=await res.json();
      if(j.status==='success'){
        draw(j.results||[]);
        if((j.results||[]).some(x=>!x.recognized)) alertUnknown();
        addEvents(j.results||[]);
        document.getElementById('fps').textContent=(j.face_count||0)+' FACE(S) · LIVE';
        refreshStats();
      }
    }catch(e){
      console.error('Recognition request failed:',e);
    }
  },'image/jpeg',.78);
  setTimeout(scan,850);
}"""
d = d[:start] + scan + d[end:]

# Make camera startup report useful errors instead of silently failing.
start = d.find('async function start(){')
end = d.find('\nconst cameraBtn=', start)
if start != -1 and end != -1:
    camera = """async function start(){
  try{
    if(!window.isSecureContext) throw new Error('Camera requires HTTPS or localhost. Open the forwarded app URL in a normal browser tab.');
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error('Camera API is unavailable in this browser/context. Open the HTTPS forwarded URL in Chrome or Edge.');
    const s=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:false});
    video.srcObject=s;
    await video.play();
    running=true;
    document.getElementById('placeholder').style.display='none';
    document.getElementById('cameraBtn').textContent='Camera running';
    scan();
  }catch(e){
    console.error('Camera start failed:',e);
    document.getElementById('placeholder').innerHTML='Camera unavailable.<br><small>'+((e&&e.name)?e.name+': ':'')+(e&&e.message?e.message:'Unknown camera error')+'</small>';
  }
}"""
    d = d[:start] + camera + d[end:]

dash.write_text(d, encoding='utf-8')
print('Camera fix applied successfully.')
print('Fixed the dashboard JavaScript syntax errors, removed stale app.js, and improved camera error reporting.')
