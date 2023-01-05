from django import forms
from django.forms import ModelForm
from .models import People


class PeopleForm(ModelForm):
    class Meta:
        model = People
        fields = ('name', 'surname', 'birthDate',
                  'genre', 'nationality', 'faceImage')

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'surname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
            'birthDate': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Data de Nascimento'}),
            'genre': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Gênero'}),
            'nationality': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Nacionalidade'}),
            'faceImage': forms.FileInput(attrs={'class': 'form-control', 'placeholder': 'Imagem'}),
        }

        labels = {
            'name': '',
            'surname': '',
            'birthDate': '',
            'genre': '',
            'nationality': '',
            'faceImage': ''
        }
