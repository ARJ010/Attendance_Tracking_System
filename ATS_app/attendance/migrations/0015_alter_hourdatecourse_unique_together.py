# Generated by Django 4.2.7 on 2025-01-25 18:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0014_alter_absentdetails_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='hourdatecourse',
            unique_together=set(),
        ),
    ]
