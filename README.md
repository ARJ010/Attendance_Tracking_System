# ATS - Attendance Tracking System

**ATS** (Attendance Tracking System) is a Django-based application designed to manage and track student attendance for courses in the Four-Year UG Programme. This system allows instructors to efficiently mark student attendance and generate reports, ensuring an organized approach to managing course participation.

## Key Features & Upgrades

- **Student Attendance Tracking**: Allows professors to mark student attendance for each class session.
- **Grace Attendance (Duty Attendance) System**: Enables HODs and administrators to assign grace credits for official reasons (e.g. NSS, NCC, Sports, Arts events). These hours are credited as "Present" in overall attendance calculations, and the specific reason is displayed in reports instead of showing the student as absent.
- **College-Wide Semester Bulk Freeze**: Administrators can freeze all active course batches college-wide for a specific semester in a single click from the main Admin Dashboard.
- **Admin Department Roster Upgrades**: Allows filtering of students and courses by semester, lists course rosters grouped neatly under their respective batches showing active/inactive badges, and embeds direct links to student individual reports, course summary reports, date-grids, and department reports.
- **Bulk Multi-Select Student Assignment Panel**: Combines nav-tabs with a collapsible, Vercel-style bulk assignment tool for HODs.
- **Print Layouts & CSS Alignment**: Aligned the print media styling of the Department Summary (`department.html`) report with the Course Summary (`report.html`) report, optimized for portrait A4 width limits and featuring signature validation blocks.
- **Security & Performance Patches**: Replaced insecure GET-based deletion endpoints with secure POST forms containing CSRF validation tokens. Optimized database queries using prefetching to resolve N+1 query bottlenecks.

## Technologies Used

- **Backend**: Django (Python)
- **Database**: MySQL (or SQLite for local development)
- **Frontend**: HTML, CSS (Vanilla), JavaScript, Bootstrap

## Setup Instructions

1. Clone this repository:
   ```bash
   git clone https://github.com/ARJ010/Attendance_Tracking_System.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Apply database migrations to sync schema to the latest version:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser to access the admin panel:
   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

6. Access the application by visiting `http://127.0.0.1:8000` in your web browser.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
