# Generated by Django 5.0.13 on 2025-04-16 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='agent_type',
            field=models.CharField(choices=[('Real Estate Agent', 'Real Estate Agent'), ('Property Manager', 'Property Manager')], default='Property Manager', max_length=50),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(blank=True, choices=[('Prospective Buyer/Tenant', 'Prospective Buyer/Tenant'), ('Agent', 'Agent')], max_length=50, null=True, verbose_name='Role'),
        ),
    ]
