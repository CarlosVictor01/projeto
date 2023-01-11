from django.http import HttpResponseRedirect
from ecdsa import SigningKey, VerifyingKey
from ecdsa.util import sigencode_der, sigdecode_der
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from people.models import People
import hashlib
import qrcode
from .forms import PeopleForm
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageFont
import pathlib
from django.http import FileResponse
from django.contrib import messages
from mrz.generator.td1 import TD1CodeGenerator
import random
import string
import os
import sys
from pathlib import Path


def index(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def form(request):
    now = date.today()
    submitted = False
    if request.method == 'POST':
        form = PeopleForm(request.POST, request.FILES)
        if form.is_valid():
            # Generating rg
            chars = string.ascii_uppercase + string.digits
            register = ''.join(random.choice(chars) for _ in range(9))

            form.save()
            identifier = form.save(commit=False)
            identifier.rg = register
            identifier.save()

            # Generating and saving the binary image data
            form.save()
            uploaded_img = form.save(commit=False)
            uploaded_img.faceImageBinary = form.cleaned_data['faceImage'].file.read(
            )
            uploaded_img.save()

            # Generating identity expiration date
            form.save()
            expiracao = form.save(commit=False)
            expiracao.expiryDate = date.fromordinal(
                now.toordinal()+1826)
            expiracao.save()

            # Preparing data to signature
            name_value = (form['name'].value())
            surname_value = (form['surname'].value())
            genre_value = (form['genre'].value())
            nationality_value = (form['nationality'].value())
            birth_date_value = (form['birthDate'].value())
            sep = ';'

            data = name_value + sep + surname_value + sep + \
                genre_value + sep + nationality_value + sep + \
                register + sep + birth_date_value

            '''
            with open('size-data-test.txt', 'w') as f:
                f.write(data)
            '''

            # Generating hash image
            img = form.cleaned_data.get("faceImage")
            obj = People.objects.create(faceImage=img)
            imgid = obj.id

            img = People.objects.get(id=imgid)
            image = img.faceImage.read()
            image_hash = hashlib.sha256(image).hexdigest()
            img.delete()

            # Reading the certificate
            with open(r"/home/carlos/Documentos/projeto/id/keys/certificado.pem", "rb") as f:
                certificate = f.read()

            # Encondig strings to bytes
            semicolon = ' ; '
            separator = semicolon.encode('utf-8')
            personal_data = data.encode('utf-8')
            personal_img_hash = image_hash.encode('utf-8')

            concatenation = certificate + separator + \
                personal_data + separator + personal_img_hash

            # Generating the hash to signature
            hash_dataGroup = hashlib.sha256(concatenation).hexdigest(
            )
            bytes_hashDataGroup = hash_dataGroup.encode('utf-8')

            # Generating the signature
            with open(r"/home/carlos/Documentos/projeto/id/keys/private_key.pem") as f:
                sk = SigningKey.from_pem(f.read())
                signature = sk.sign_deterministic(
                    bytes_hashDataGroup, sigencode=sigencode_der)

            '''
            with open('size-sig-test.sig', 'wb') as f:
                f.write(signature)
            '''

            # Reading info
            with open(r"/home/carlos/Documentos/projeto/version", "rb") as f:
                header = f.read()

            '''
            testSize = os.path.getsize(
                "/home/carlos/Documentos/projeto/version")
            print(testSize)
            '''

            # Generating the qrcode
            qr = qrcode.QRCode(
                version=22,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )

            qr.add_data(header)
            qr.add_data(personal_data)
            qr.add_data(personal_img_hash)
            qr.add_data(certificate)
            qr.add_data(signature)
            qr.make(fit=True)

            img_qrcode = qr.make_image(fill_color="black",
                                       back_color="white")
            img_qrcode.save('qr_code.png')

            # Formatting expiration date for the identity front
            formated_expiry_date = (expiracao.expiryDate).strftime(
                '%d/%m/%Y')

            # Formatting and preparing data for MRZ
            mrz_expiry_date = (expiracao.expiryDate).strftime('%y%m%d'[0:8])

            unformatted_date = birth_date_value
            date_object = datetime.strptime(
                unformatted_date, '%d/%m/%Y').date()
            mrz_birth_date = date_object.strftime('%y%m%d'[0:8])

            document_type = "ID"
            country = "Brazil"

            # Generating the MRZ
            mrzCode = str(TD1CodeGenerator(document_type, nationality_value,
                                           register, mrz_birth_date, genre_value,
                                           mrz_expiry_date, country, surname_value,
                                           name_value))

            # Reading fonts
            font_1 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Bold.ttf", size=14)
            font_3 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Medium.ttf", size=17)

            # Reading template
            template = Image.open(
                r"/home/carlos/Documentos/projeto/people/templates/id_templates/template.png")

            # Writing template
            faceImage = Image.open(
                form.cleaned_data['faceImage']).resize((115, 152))
            template.paste(faceImage, (40, 79, 155, 231))
            draw = ImageDraw.Draw(template)
            draw.text(
                (181, 83), form.cleaned_data['name'], font=font_1, width=31, fill='black')
            draw.text(
                (181, 119), form.cleaned_data['surname'], font=font_1, width=31, fill='black')
            draw.text((181, 152), birth_date_value, font=font_1, fill='black')
            draw.text(
                (295, 152), form.cleaned_data['genre'], font=font_1, fill='black')
            draw.text((181, 184), str(formated_expiry_date),
                      font=font_1, fill='black')
            draw.text(
                (295, 184), form.cleaned_data['nationality'], font=font_1, fill='black')
            draw.text((181, 216), register, font=font_1, fill='black')
            draw.text((410, 200), mrzCode, font=font_3, fill='black')

            # Pasting the qrcode
            qrcodeImage = Image.open("qr_code.png").resize((186, 190))
            template.paste(qrcodeImage, (474, 8, 660, 198))

            # Generating PDF
            template.save('id.png', quality=100, optimize=True)
            img = Image.open('id.png')

            img_final = Image.new("RGB", (756, 275), "white")
            img_final.paste(img)
            img_final.save("id_final.pdf")

            return HttpResponseRedirect('form?submitted=True')
    else:
        form = PeopleForm
        if 'submitted' in request.GET:
            submitted = True
    return render(request, 'form.html', {'form': form, 'submitted': submitted})


def download_id(request, filename=''):
    file_server = pathlib.Path('id_final.pdf')
    if not file_server.exists():
        messages.error(request, 'file not found.')
    else:
        file_to_download = open(str(file_server), 'rb')
        response = FileResponse(
            file_to_download, content_type='application/force-download')
        response['Content-Disposition'] = 'inline; filename="identidade"'
        return response
    return redirect('download_id.html')


def search(request):
    rg_submitted = False
    if request.method == "POST":
        searched_id = request.POST['searched']
        people = People.objects.get(rg=searched_id)

        # Getting hash image
        image = people.faceImage.read()
        image_hash = hashlib.sha256(image).hexdigest()

        # Getting and formatting identity expiration date
        formated_expiry_date = (people.expiryDate).strftime(
            '%d/%m/%Y')
        mrz_expiry_date = (people.expiryDate).strftime('%y%m%d'[0:8])

        # Getting and formatting birth date
        formated_birth = (people.birthDate).strftime(
            '%d/%m/%Y')

        # Getting and Preparing data to signature
        name_value = people.name
        surname_value = people.surname
        genre_value = people.genre
        nationality_value = people.nationality
        birth_date_value = formated_birth
        register = people.rg
        sep = ';'

        data = name_value + sep + surname_value + sep + genre_value + sep + \
            nationality_value + sep + register + sep + birth_date_value

        # Reading the certificate
        with open(r"/home/carlos/Documentos/projeto/id/keys/certificado.pem", "rb") as f:
            certificate = f.read()

        # Encondig strings to bytes
        semicolon = ' ; '
        separator = semicolon.encode('utf-8')
        personal_data = data.encode('utf-8')
        personal_img_hash = image_hash.encode('utf-8')

        concatenation = certificate + separator + \
            personal_data + separator + personal_img_hash

        # Generating the hash to signature
        hash_dataGroup = hashlib.sha256(concatenation).hexdigest(
        )
        bytes_hashDataGroup = hash_dataGroup.encode('utf-8')

        # Generating the signature
        with open(r"/home/carlos/Documentos/projeto/id/keys/private_key.pem") as f:
            sk = SigningKey.from_pem(f.read())
            signature = sk.sign_deterministic(
                bytes_hashDataGroup, sigencode=sigencode_der)

        # Reading info
            with open(r"/home/carlos/Documentos/projeto/version", "rb") as f:
                header = f.read()

        # Generating the qrcode
        qr = qrcode.QRCode(
            version=22,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        qr.add_data(header)
        qr.add_data(personal_data)
        qr.add_data(personal_img_hash)
        qr.add_data(certificate)
        qr.add_data(signature)
        qr.make(fit=True)

        img_qrcode = qr.make_image(fill_color="black", back_color="white")
        img_qrcode.save('qr_code.png')

        date_object = people.birthDate
        mrz_birth_date = date_object.strftime('%y%m%d'[0:8])

        document_type = "ID"
        country = "Brazil"

        # Generating MRZ
        mrzCode = str(TD1CodeGenerator(document_type, nationality_value, register, mrz_birth_date, genre_value,
                                       mrz_expiry_date, country, surname_value, name_value))

        # Reading fonts
        font_1 = ImageFont.truetype(
            r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Bold.ttf", size=14)
        font_3 = ImageFont.truetype(
            r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Medium.ttf", size=17)

        # Reading template
        template = Image.open(
            r"/home/carlos/Documentos/projeto/people/templates/id_templates/template.png")

        # Writing template
        faceImage = Image.open(people.faceImage).resize((115, 152))
        template.paste(faceImage, (40, 79, 155, 231))
        draw = ImageDraw.Draw(template)
        draw.text(
            (181, 83), people.name, font=font_1, width=31, fill='black')
        draw.text(
            (181, 119), people.surname, font=font_1, width=31, fill='black')
        draw.text((181, 152), birth_date_value, font=font_1, fill='black')
        draw.text(
            (295, 152), people.genre, font=font_1, fill='black')
        draw.text((181, 184), str(formated_expiry_date),
                  font=font_1, fill='black')
        draw.text(
            (295, 184), people.nationality, font=font_1, fill='black')
        draw.text((181, 216), register, font=font_1, fill='black')
        draw.text((410, 200), mrzCode, font=font_3, fill='black')

        # Pasting the qrcode
        qrcodeImage = Image.open("qr_code.png").resize((186, 190))
        template.paste(qrcodeImage, (474, 8, 660, 198))

        # Generating PDF
        template.save('id.png', quality=100, optimize=True)
        img = Image.open('id.png')

        img_final = Image.new("RGB", (756, 275), "white")
        img_final.paste(img)
        img_final.save("id_final.pdf")

        return HttpResponseRedirect('search?rg_submitted=True', {'people': people})
    else:
        if 'rg_submitted' in request.GET:
            rg_submitted = True
    return render(request, 'search.html', {'rg_submitted': rg_submitted})
