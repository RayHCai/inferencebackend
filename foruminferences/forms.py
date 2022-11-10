from django import forms

class PostRelationsForm(forms.Form):
    forum_id = forms.UUIDField()
    post_id = forms.IntegerField()
    
    question = forms.CharField()
    similarity = forms.FloatField()
