from django.contrib import admin
from django.urls import path

from forums.views import ForumsView, ForumPostsView
from foruminferences.views import InferencesView, PostRelationsView, QuestionInferenceView, DeleteInferencesView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('forums/', ForumsView.as_view()),
    path('forumposts/', ForumPostsView.as_view()),
    path('foruminference/', InferencesView.as_view()),
    path('postrelations/', PostRelationsView.as_view()),
    path('questioninference/', QuestionInferenceView.as_view()),
    path('deleteinferences/', DeleteInferencesView.as_view()),
]
