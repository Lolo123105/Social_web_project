from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image',)

    def cleaned_text(self):
        data = self.cleaned_data['text']

        if data is None:
            raise forms.ValidationError(
                'Вы обязательно должны написать текст!')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

    def cleaned_text(self):
        data = self.cleaned_data['text']

        if data is None:
            raise forms.ValidationError(
                'Вы обязательно должны написать текст!')
        return data
