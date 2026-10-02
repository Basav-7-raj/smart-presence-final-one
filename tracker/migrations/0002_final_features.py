from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('tracker','0001_initial')]
    operations=[
      migrations.AddField(model_name='personprofile',name='active',field=models.BooleanField(default=True)),
      migrations.AddField(model_name='personprofile',name='updated_at',field=models.DateTimeField(auto_now=True)),
      migrations.AddField(model_name='presencerecord',name='confidence',field=models.FloatField(default=0.0)),
      migrations.AddField(model_name='presencerecord',name='liveness_passed',field=models.BooleanField(default=True)),
      migrations.AddField(model_name='unknownevent',name='acknowledged',field=models.BooleanField(default=False)),
      migrations.AddField(model_name='unknownevent',name='message',field=models.CharField(default='Unknown person detected',max_length=200)),
      migrations.AddField(model_name='unknownevent',name='severity',field=models.CharField(default='HIGH',max_length=20)),
      migrations.AddField(model_name='unknownevent',name='snapshot',field=models.ImageField(blank=True,null=True,upload_to='unknown_events/')),
      migrations.CreateModel(name='SystemEvent',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('event_type',models.CharField(choices=[('verified','Verified'),('unknown','Unknown'),('liveness','Liveness Failed'),('system','System'),('camera','Camera')],max_length=20)),('message',models.CharField(max_length=255)),('timestamp',models.DateTimeField(auto_now_add=True)),('severity',models.CharField(default='INFO',max_length=20)),('person',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to='tracker.personprofile'))]),
      migrations.CreateModel(name='SystemSetting',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('key',models.CharField(max_length=80,unique=True)),('value',models.CharField(max_length=255))]),
    ]
