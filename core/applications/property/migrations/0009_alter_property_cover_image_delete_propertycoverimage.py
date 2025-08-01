# Generated by Django 5.0.13 on 2025-07-23 13:47

import core.helper.media
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('property', '0008_propertycoverimage_property_cover_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to=core.helper.media.MediaHelper.get_image_upload_path),
        ),
        migrations.DeleteModel(
            name='PropertyCoverImage',
        ),
    ]
