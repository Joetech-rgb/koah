from django.contrib import admin
from .models import CandidateProfile, Skill, Experience

admin.site.register(CandidateProfile)
admin.site.register(Skill)
admin.site.register(Experience)
