from django import forms

class ForumPostsForm(forms.Form):
    post_id = forms.UUIDField()
    forum_id = forms.UUIDField()
