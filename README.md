# ATS - Attendance Tracking System

**ATS** (Attendance Tracking System) is a Django-based application designed to manage and track student attendance for courses in the new Four-Year UG Programme. This system allows instructors to efficiently mark student attendance and generate reports, ensuring an organized approach to managing course participation.

## Features

- **Student Attendance Tracking**: Allows professors to mark student attendance for each class session.
- **Course Management**: Organize and manage courses, including student enrollments and instructors.
- **Automated Reports**: Generate attendance reports and track overall student participation.
- **User-Friendly Interface**: Simple UI for instructors to take attendance by selecting student names.

## Technologies Used

- **Backend**: Django (Python)
- **Database**: MySQL (or SQLite for local development)
- **Frontend**: HTML, CSS, JavaScript
- **Other**: Bootstrap for UI styling

## Setup Instructions

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ATS.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Apply database migrations:
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

## Screenshots

(Include some screenshots of the application interface here)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



