from django.core.management.base import BaseCommand
from attendance.models import (
    Course, Student, Teacher, Department,
    StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,  # old models
    Batch, StudentBatch, TeacherBatch, HourDateBatch, NewAbsentDetails  # new models
)
from collections import defaultdict


class Command(BaseCommand):
    help = "Migrate attendance data from course-based models to batch-based models"

    def handle(self, *args, **kwargs):
        print("Starting batch migration...")

        # Map (course_id, year) to Batch
        course_year_to_batch = {}

        # STEP 1: Create Batches
        print("Creating Batches...")
        for sc in StudentCourse.objects.all():
            key = (sc.course_id, sc.year)
            if key not in course_year_to_batch:
                batch = Batch.objects.create(
                    course_id=sc.course_id,
                    academic_year=sc.year,
                    part='A',  # You can improve this logic if needed
                    active=True
                )
                course_year_to_batch[key] = batch
                print(f"Created Batch: {batch.id} for Course {sc.course_id}, Year {sc.year}")

        # STEP 2: Create StudentBatch links
        print("Linking Students to Batches...")
        for sc in StudentCourse.objects.all():
            batch = course_year_to_batch.get((sc.course_id, sc.year))
            if batch:
                StudentBatch.objects.get_or_create(student_id=sc.student_id, batch=batch)

        # STEP 3: Create TeacherBatch links
        print("Linking Teachers to Batches...")
        for tc in TeacherCourse.objects.all():
            batch = course_year_to_batch.get((tc.course_id, tc.year))
            if batch:
                TeacherBatch.objects.get_or_create(teacher_id=tc.teacher_id, batch=batch)

        # STEP 4: Create HourDateBatch from HourDateCourse
        print("Creating HourDateBatch entries...")
        hdc_to_hdb_map = {}
        for hdc in HourDateCourse.objects.all():
            batch = course_year_to_batch.get((hdc.course_id, hdc.year))
            if not batch:
                continue
            # Find or create TeacherBatch
            tb = TeacherBatch.objects.filter(teacher=hdc.teacher, batch=batch).first()
            if not tb:
                continue
            hdb = HourDateBatch.objects.create(
                teacher_batch=tb,
                date=hdc.date,
                hour=hdc.hour
            )
            hdc_to_hdb_map[hdc.id] = hdb
            print(f"Created HourDateBatch {hdb.id} from HourDateCourse {hdc.id}")

        # STEP 5: Migrate AbsentDetails
        print("Migrating attendance records...")
        migrated_count = 0
        for ad in AbsentDetails.objects.all():
            hdb = hdc_to_hdb_map.get(ad.hour_date_course_id)
            if not hdb:
                continue
            NewAbsentDetails.objects.get_or_create(
                hour_date_batch=hdb,
                student=ad.student,
                status=ad.status
            )
            migrated_count += 1
        print(f"Migrated {migrated_count} attendance records.")

        print("✅ Batch migration completed.")
