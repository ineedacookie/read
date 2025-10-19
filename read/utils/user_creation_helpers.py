"""
User creation helper functions to reduce code duplication in user creation processes.
Used primarily by management commands and bulk user creation operations.
"""

from django.contrib.auth import get_user_model
from datetime import date, timedelta
import random


def create_user_with_defaults(user_type, school, username, email, password, first_name, last_initial, **extra_fields):
    """
    Create a user with standard defaults applied.
    
    Args:
        user_type: Type of user ('student', 'teacher', 'parent', 'administrator')
        school: School object
        username: Username for the user
        email: Email for the user
        password: Password for the user
        first_name: First name
        last_initial: Last initial
        **extra_fields: Additional fields to set
    
    Returns:
        User: Created user instance
    """
    User = get_user_model()  # Get the user model lazily
    
    defaults = {
        'user_type': user_type,
        'school': school,
        'verified': True,
        'password_change_required': False,
        **extra_fields
    }
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_initial=last_initial,
        **defaults
    )
    
    return user


def create_administrator(school, school_index, admin_data=None):
    """
    Create an administrator for a school.
    
    Args:
        school: School object
        school_index: Index of the school (for naming)
        admin_data: Optional dictionary with admin data
    
    Returns:
        User: Created administrator
    """
    if admin_data is None:
        admin_data = {
            'first_name': "Sarah" if school_index == 0 else "Michael",
            'last_initial': "A" if school_index == 0 else "B"
        }
    
    admin = create_user_with_defaults(
        user_type="administrator",
        school=school,
        username=f"admin{school_index + 1}",
        email=f"admin@school{school_index + 1}.edu",
        password="password123",
        first_name=admin_data['first_name'],
        last_initial=admin_data['last_initial']
    )
    
    return admin


def create_teachers(school, school_index, teacher_data=None, count=4):
    """
    Create teachers for a school.
    
    Args:
        school: School object
        school_index: Index of the school (for naming)
        teacher_data: Optional list of teacher data dictionaries
        count: Number of teachers to create
    
    Returns:
        list: Created teacher users
    """
    if teacher_data is None:
        teacher_data = [
            ("Emma", "S", "emma.smith"),
            ("James", "J", "james.johnson"),
            ("Lisa", "W", "lisa.williams"),
            ("David", "B", "david.brown"),
            ("Maria", "G", "maria.garcia")
        ]
    
    teachers = []
    for i, (first_name, last_initial, username) in enumerate(teacher_data[:count]):
        teacher = create_user_with_defaults(
            user_type="teacher",
            school=school,
            username=f"{username}_{school_index + 1}",
            email=f"{username}@school{school_index + 1}.edu",
            password="password123",
            first_name=first_name,
            last_initial=last_initial
        )
        teachers.append(teacher)
    
    return teachers


def create_students(school, school_index, student_data=None, count=18):
    """
    Create students for a school.
    
    Args:
        school: School object
        school_index: Index of the school (for naming)
        student_data: Optional list of student data tuples
        count: Number of students to create
    
    Returns:
        list: Created student users
    """
    if student_data is None:
        student_data = [
            ("Alex", "M"), ("Bailey", "S"), ("Charlie", "J"), ("Dana", "L"),
            ("Ethan", "W"), ("Fiona", "H"), ("Gabriel", "R"), ("Hannah", "K"),
            ("Ian", "P"), ("Julia", "T"), ("Kevin", "N"), ("Luna", "C"),
            ("Mason", "D"), ("Nora", "F"), ("Oscar", "V"), ("Piper", "B"),
            ("Quinn", "G"), ("Riley", "A"), ("Sage", "E"), ("Taylor", "Z")
        ]
    
    students = []
    for i, (first_name, last_initial) in enumerate(student_data[:count]):
        student = create_user_with_defaults(
            user_type="student",
            school=school,
            username=f"student{i + 1}_school{school_index + 1}",
            email=f"student{i + 1}@school{school_index + 1}.edu",
            password="password123",
            first_name=first_name,
            last_initial=last_initial
        )
        students.append(student)
    
    return students


def create_parents(school, school_index, parent_data=None, count=10):
    """
    Create parents for a school.
    
    Args:
        school: School object
        school_index: Index of the school (for naming)
        parent_data: Optional list of parent data tuples
        count: Number of parents to create
    
    Returns:
        list: Created parent users
    """
    if parent_data is None:
        parent_data = [
            ("Jennifer", "M", "jennifer.martinez"),
            ("Robert", "D", "robert.davis"),
            ("Michelle", "W", "michelle.wilson"),
            ("Christopher", "A", "christopher.anderson"),
            ("Amanda", "T", "amanda.taylor"),
            ("Matthew", "L", "matthew.lopez"),
            ("Jessica", "H", "jessica.hernandez"),
            ("Andrew", "K", "andrew.king"),
            ("Ashley", "Y", "ashley.young"),
            ("Joshua", "S", "joshua.scott"),
            ("Stephanie", "G", "stephanie.green"),
            ("Daniel", "C", "daniel.clark")
        ]
    
    parents = []
    for i, (first_name, last_initial, username) in enumerate(parent_data[:count]):
        parent = create_user_with_defaults(
            user_type="parent",
            school=school,
            username=f"{username}_{school_index + 1}",
            email=f"{username}@parent{school_index + 1}.com",
            password="password123",
            first_name=first_name,
            last_initial=last_initial
        )
        parents.append(parent)
    
    return parents


def create_school_users(school, school_index):
    """
    Create all types of users for a school.
    
    Args:
        school: School object
        school_index: Index of the school
    
    Returns:
        dict: Dictionary with lists of created users by type
    """
    users = {
        'administrators': [],
        'teachers': [],
        'students': [],
        'parents': []
    }
    
    # Create administrator
    admin = create_administrator(school, school_index)
    users['administrators'].append(admin)
    
    # Create teachers
    teachers = create_teachers(school, school_index)
    users['teachers'].extend(teachers)
    
    # Create students
    students = create_students(school, school_index)
    users['students'].extend(students)
    
    # Create parents
    parents = create_parents(school, school_index)
    users['parents'].extend(parents)
    
    return users


def create_classrooms_for_school(school, teachers, classroom_names=None):
    """
    Create classrooms for a school with assigned teachers.
    
    Args:
        school: School object
        teachers: List of teacher users
        classroom_names: Optional list of classroom names
    
    Returns:
        list: Created classroom objects
    """
    # Import model lazily to avoid circular imports
    from users.models import Classroom
    
    if classroom_names is None:
        classroom_names = [
            f"Grade 3A - {teachers[0].first_name}'s Class" if len(teachers) > 0 else "Grade 3A",
            f"Grade 3B - {teachers[1].first_name}'s Class" if len(teachers) > 1 else "Grade 3B",
            f"Grade 4A - {teachers[2].first_name}'s Class" if len(teachers) > 2 else "Grade 4A",
            f"Grade 4B - {teachers[3].first_name}'s Class" if len(teachers) > 3 else "Grade 4B"
        ]
    
    classrooms = []
    for i, name in enumerate(classroom_names):
        classroom = Classroom.objects.create(
            name=name,
            school=school
        )
        # Assign teacher if available
        if i < len(teachers):
            classroom.teachers.add(teachers[i])
        classrooms.append(classroom)
    
    return classrooms


def create_reading_groups_for_school(school, teachers, group_names=None):
    """
    Create reading groups for a school with assigned managers.
    
    Args:
        school: School object
        teachers: List of teacher users
        group_names: Optional list of group names
    
    Returns:
        list: Created reading group objects
    """
    # Import model lazily to avoid circular imports
    from users.models import ReadingGroup
    if group_names is None:
        group_names = [
            "Advanced Readers",
            "Story Explorers",
            "Book Detectives"
        ]
    
    reading_groups = []
    for i, name in enumerate(group_names):
        group = ReadingGroup.objects.create(
            name=name,
            school=school
        )
        # Assign manager if available
        if i < len(teachers):
            group.managers.add(teachers[i])
        reading_groups.append(group)
    
    return reading_groups


def assign_students_to_classrooms(students, classrooms):
    """
    Evenly distribute students across classrooms.
    
    Args:
        students: List of student users
        classrooms: List of classroom objects
    """
    if not classrooms:
        return
    
    students_per_classroom = len(students) // len(classrooms)
    remaining_students = len(students) % len(classrooms)
    
    student_index = 0
    for i, classroom in enumerate(classrooms):
        # Calculate how many students this classroom should get
        num_students = students_per_classroom
        if i < remaining_students:  # Distribute remaining students to first few classrooms
            num_students += 1
        
        # Assign students to this classroom
        classroom_students = students[student_index:student_index + num_students]
        for student in classroom_students:
            classroom.students.add(student)
        
        student_index += num_students


def assign_students_to_reading_groups(students, reading_groups):
    """
    Randomly assign students to reading groups with overlap.
    
    Args:
        students: List of student users
        reading_groups: List of reading group objects
    """
    for group in reading_groups:
        # Each reading group gets 30-60% of students
        group_size = random.randint(int(len(students) * 0.3), int(len(students) * 0.6))
        group_students = random.sample(students, min(group_size, len(students)))
        
        for student in group_students:
            group.students.add(student)


def create_parent_child_relationships(school, students, parents):
    """
    Create realistic parent-child relationships.
    
    Args:
        school: School object
        students: List of student users
        parents: List of parent users
    
    Returns:
        int: Number of relationships created
    """
    # Import model lazily to avoid circular imports
    from users.models import StudentParentRelation
    
    relationships_created = 0
    student_index = 0
    
    for parent in parents:
        # Random number of children (1-3, weighted towards 2)
        num_children = random.choices([1, 2, 3], weights=[3, 5, 2])[0]
        
        for _ in range(num_children):
            if student_index < len(students):
                StudentParentRelation.objects.create(
                    school=school,
                    student=students[student_index],
                    parent=parent
                )
                relationships_created += 1
                student_index += 1
    
    # Ensure any remaining students have parents
    while student_index < len(students):
        # Assign to a random existing parent
        parent = random.choice(parents)
        StudentParentRelation.objects.create(
            school=school,
            student=students[student_index],
            parent=parent
        )
        relationships_created += 1
        student_index += 1
    
    return relationships_created


def setup_school_structure(school, teachers, students):
    """
    Set up the complete school structure with classrooms, groups, and assignments.
    
    Args:
        school: School object
        teachers: List of teacher users
        students: List of student users
    
    Returns:
        tuple: (classrooms, reading_groups)
    """
    # Create classrooms and reading groups
    classrooms = create_classrooms_for_school(school, teachers)
    reading_groups = create_reading_groups_for_school(school, teachers)
    
    # Assign students to classrooms and groups
    assign_students_to_classrooms(students, classrooms)
    assign_students_to_reading_groups(students, reading_groups)
    
    return classrooms, reading_groups


def create_superuser_if_needed(username='temp', email='temp@temp.com', password='temp'):
    """
    Create a superuser if it doesn't already exist.
    
    Args:
        username: Username for superuser
        email: Email for superuser
        password: Password for superuser
    
    Returns:
        User: Superuser instance (new or existing)
    """
    if User.objects.filter(username=username).exists():
        return User.objects.get(username=username)
    
    superuser = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name='Super',
        last_initial='U'
    )
    
    return superuser


def get_default_school_names():
    """
    Get default school names for sample data.
    
    Returns:
        list: List of default school names
    """
    return [
        "Riverside Elementary School",
        "Oak Valley Middle School"
    ]


def create_school_with_data(school_index, school_name=None):
    """
    Create a complete school with all users and structure.
    
    Args:
        school_index: Index of the school being created
        school_name: Optional custom school name
    
    Returns:
        tuple: (school, users_dict, classrooms, reading_groups, relationships_count)
    """
    # Import model lazily to avoid circular imports
    from users.models import School
    
    # Create school
    if school_name is None:
        default_names = get_default_school_names()
        school_name = default_names[school_index] if school_index < len(default_names) else f"Sample School {school_index + 1}"
    
    school = School.objects.create(name=school_name)
    
    # Create users
    users = create_school_users(school, school_index)
    
    # Set up school structure
    classrooms, reading_groups = setup_school_structure(
        school, 
        users['teachers'], 
        users['students']
    )
    
    # Create parent-child relationships
    relationships_count = create_parent_child_relationships(
        school, 
        users['students'], 
        users['parents']
    )
    
    return school, users, classrooms, reading_groups, relationships_count


def create_superuser_if_needed():
    """
    Create a superuser for Django admin access if one doesn't already exist.
    
    Returns:
        User: The created or existing superuser
    """
    User = get_user_model()  # Get the user model lazily
    
    # Check if a superuser already exists
    if User.objects.filter(is_superuser=True).exists():
        return User.objects.filter(is_superuser=True).first()
    
    # Create the superuser
    superuser = User.objects.create_superuser(
        username='admin',
        email='temp@temp.com',
        password='temp',
        first_name='Super',
        last_initial='A'
    )
    
    return superuser
