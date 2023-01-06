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

            # Generating the qrcode
            info_qr = 'version=22;correction=low;box_size=10; \
                border=4'

            qr = qrcode.QRCode(
                version=22,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )

            qr.add_data(info_qr)
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
            code = str(TD1CodeGenerator(document_type, nationality_value,
                                        register, mrz_birth_date, genre_value,
                                        mrz_expiry_date, country, surname_value,
                                        name_value))

            # Writing template front
            font_1 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Bold.ttf", size=30)
            templateFront = Image.open(
                r"/home/carlos/Documentos/projeto/people/templates/id_templates/front.png")
            pic = Image.open(form.cleaned_data['faceImage']).resize((275, 367))
            templateFront.paste(pic, (132, 161, 407, 528))
            draw = ImageDraw.Draw(templateFront)
            draw.text(
                (487, 185), form.cleaned_data['name'], font=font_1, width=31,
                fill='black')
            draw.text(
                (487, 265), form.cleaned_data['surname'], font=font_1, width=31,
                fill='black')
            draw.text(
                (487, 340), form.cleaned_data['genre'], font=font_1,
                fill='black')
            draw.text(
                (733, 340), form.cleaned_data['nationality'], font=font_1,
                fill='black')
            draw.text(
                (487, 420), register, font=font_1, fill='black')
            draw.text(
                (733, 420), birth_date_value, font=font_1, fill='black')
            draw.text((487, 497), str(formated_expiry_date),
                      font=font_1, fill='black')
            templateFront.save('id_front.png', quality=100, optimize=True)

            # Writing template verse
            font_3 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Medium.ttf", size=25)
            templateVerse = Image.open(
                r"/home/carlos/Documentos/projeto/people/templates/id_templates/verse.png")
            pic = Image.open("qr_code.png").resize((460, 470))
            templateVerse.paste(pic, (274, 27, 734, 497))
            draw = ImageDraw.Draw(templateVerse)
            draw.text((280, 525), code, font=font_3, fill='black')
            templateVerse.save('id_verse.png', quality=100, optimize=True)

            # Generating final identity image
            img_front = Image.open('id_front.png')
            img_verse = Image.open("id_verse.png")

            resized_img_front = img_front.resize((599, 420))
            resized_img_verse = img_verse.resize((599, 420))

            img_final = Image.new("RGB", (1200, 420), "white")

            img_final.paste(resized_img_front, (0, 0))
            img_final.paste(resized_img_verse, (600, 0))

            img_final.save("id_final.pdf")
            # print(resized_img_front.size)
            # print(resized_img_verse.size)

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

        # Generating the qrcode
            info_qr = 'version=22;correction=low;box_size=10; \
                border=4'

            qr = qrcode.QRCode(
                version=22,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )

            qr.add_data(info_qr)
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
            code = str(TD1CodeGenerator(document_type, nationality_value, register, mrz_birth_date, genre_value,
                                        mrz_expiry_date, country, surname_value, name_value))

            # Writing template verse
            font_3 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Medium.ttf", size=25)
            templateVerse = Image.open(
                r"/home/carlos/Documentos/projeto/people/templates/id_templates/verse.png")
            pic = Image.open("qr_code.png").resize((460, 470))
            templateVerse.paste(pic, (274, 27, 734, 497))
            draw = ImageDraw.Draw(templateVerse)
            draw.text((280, 525), code, font=font_3, fill='black')
            templateVerse.save('id_verse.png', quality=100, optimize=True)

            # Writing template front
            font_1 = ImageFont.truetype(
                r"/home/carlos/Documentos/projeto/people/templates/fonts/OpenSans-Bold.ttf", size=30)
            templateFront = Image.open(
                r"/home/carlos/Documentos/projeto/people/templates/id_templates/front.png")
            pic = Image.open(people.faceImage).resize((275, 367))
            templateFront.paste(pic, (132, 161, 407, 528))
            draw = ImageDraw.Draw(templateFront)

            draw.text((487, 185), people.name, font=font_1, width=31,
                      fill='black')
            draw.text((487, 265), people.surname, font=font_1, width=31,
                      fill='black')
            draw.text(
                (487, 340), people.genre, font=font_1, fill='black')
            draw.text(
                (733, 340), people.nationality, font=font_1,  fill='black')
            draw.text(
                (487, 420), register, font=font_1, fill='black')
            draw.text(
                (733, 420), birth_date_value, font=font_1, fill='black')
            draw.text((487, 497), str(formated_expiry_date),
                      font=font_1, fill='black')
            templateFront.save('id_front.png', quality=100, optimize=True)

            # Generating final identity image
            img_front = Image.open('id_front.png')
            img_verse = Image.open("id_verse.png")

            resized_img_front = img_front.resize((599, 420))
            resized_img_verse = img_verse.resize((599, 420))

            img_final = Image.new("RGB", (1200, 420), "white")

            img_final.paste(resized_img_front, (0, 0))
            img_final.paste(resized_img_verse, (600, 0))

            img_final.save("id_final.pdf")
            # print(resized_img_front.size)
            # print(resized_img_verse.size)

        return HttpResponseRedirect('search?rg_submitted=True', {'people': people})
    else:
        if 'rg_submitted' in request.GET:
            rg_submitted = True
    return render(request, 'search.html', {'rg_submitted': rg_submitted})
