import json
from django.db import models

class PersonProfile(models.Model):
    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50, unique=True)
    encoding_json = models.TextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_encoding(self, feature): self.encoding_json = json.dumps(feature)
    def get_encoding(self): return json.loads(self.encoding_json)
    def __str__(self): return f"{self.name} ({self.student_id})"

class PresenceRecord(models.Model):
    person = models.ForeignKey(PersonProfile, on_delete=models.CASCADE, related_name='presence_records')
    timestamp = models.DateTimeField(auto_now_add=True)
    device_source = models.CharField(max_length=120, default='Browser Webcam')
    confidence = models.FloatField(default=0.0)
    liveness_passed = models.BooleanField(default=True)
    class Meta: ordering = ['-timestamp']

class UnknownEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    best_score = models.FloatField(default=0.0)
    liveness_passed = models.BooleanField(default=False)
    source = models.CharField(max_length=120, default='Browser Webcam')
    snapshot = models.ImageField(upload_to='unknown_events/', blank=True, null=True)
    acknowledged = models.BooleanField(default=False)
    severity = models.CharField(max_length=20, default='HIGH')
    message = models.CharField(max_length=200, default='Unknown person detected')
    class Meta: ordering = ['-timestamp']

class SystemEvent(models.Model):
    EVENT_TYPES = [('verified','Verified'),('unknown','Unknown'),('liveness','Liveness Failed'),('system','System'),('camera','Camera')]
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=20, default='INFO')
    person = models.ForeignKey(PersonProfile, null=True, blank=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['-timestamp']

class SystemSetting(models.Model):
    key = models.CharField(max_length=80, unique=True)
    value = models.CharField(max_length=255)
    def __str__(self): return f'{self.key}={self.value}'
