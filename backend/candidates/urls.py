from rest_framework.routers import DefaultRouter

from .views import CandidateViewSet, SkillViewSet

router = DefaultRouter()
router.register(r"candidates", CandidateViewSet, basename="candidate")
router.register(r"skills", SkillViewSet, basename="skill")

urlpatterns = router.urls
