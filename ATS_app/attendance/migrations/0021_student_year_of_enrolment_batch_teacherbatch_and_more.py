import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0020_student_roll_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='year_of_enrolment',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.CreateModel(
            name='Batch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=50)),
                ('part', models.CharField(max_length=50)),
                ('active', models.BooleanField(default=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.course')),
            ],
        ),
        migrations.CreateModel(
            name='TeacherBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.batch')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.teacher')),
            ],
            options={
                'unique_together': {('teacher', 'batch')},
            },
        ),
        migrations.CreateModel(
            name='HourDateBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('hour', models.PositiveSmallIntegerField(choices=[(1, 'Hour 1'), (2, 'Hour 2'), (3, 'Hour 3'), (4, 'Hour 4'), (5, 'Hour 5')])),
                ('year', models.PositiveIntegerField(editable=False)),
                ('teacher_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.teacherbatch')),
            ],
        ),
        migrations.CreateModel(
            name='StudentBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.batch')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.student')),
            ],
            options={
                'unique_together': {('student', 'batch')},
            },
        ),
        migrations.CreateModel(
            name='NewAbsentDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.BooleanField(default=False)),
                ('hour_date_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.hourdatebatch')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='attendance.student')),
            ],
            options={
                'unique_together': {('hour_date_batch', 'student')},
            },
        ),
    ]
