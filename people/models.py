from django.db import models
from django.db import models


class People(models.Model):
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino')
    )

    NATIONALITY_CHOICES = (
        ('BRA', 'Brasileiro(a)'),
        ('PRT', 'Português')
    )

    rg = models.CharField(max_length=9, unique=True, blank=True, null=True)
    name = models.CharField('name', max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=255, blank=True, null=True)
    birthDate = models.DateField(blank=True, null=True)
    genre = models.CharField(max_length=10, choices=SEXO_CHOICES, default='M')
    nationality = models.CharField(
        max_length=10, choices=NATIONALITY_CHOICES, default='BRA')
    faceImage = models.ImageField(verbose_name=(
        'faceImage'), upload_to='images', blank=True)
    faceImageBinary = models.BinaryField(null=True)
    expiryDate = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name
