from django import forms

class PostRelationsForm(forms.Form):
    question = forms.CharField()
    forum_id = forms.UUIDField()
    post_id = forms.IntegerField()
