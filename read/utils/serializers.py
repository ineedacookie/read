"""
Serializers for API responses.
Control exactly what data gets sent to frontend, reducing payload sizes.
"""


class BaseSerializer:
    """Base serializer with field selection capability"""
    default_fields = []
    optional_fields = []
    
    @classmethod
    def serialize(cls, obj, fields=None):
        """
        Serialize an object with specified fields.
        
        Args:
            obj: Model instance to serialize
            fields: List of fields to include (default: default_fields)
            
        Returns:
            dict: Serialized data
        """
        if fields is None:
            fields = cls.default_fields
        
        result = {}
        for field in fields:
            if hasattr(cls, f'get_{field}'):
                # Use custom getter if defined
                result[field] = getattr(cls, f'get_{field}')(obj)
            elif hasattr(obj, field):
                # Direct attribute access
                value = getattr(obj, field)
                # Handle callable attributes
                if callable(value):
                    result[field] = value()
                else:
                    result[field] = value
        
        return result
    
    @classmethod
    def serialize_many(cls, queryset, fields=None):
        """Serialize a queryset or list of objects"""
        return [cls.serialize(obj, fields) for obj in queryset]


class StudentSerializer(BaseSerializer):
    """
    Serializer for Student data.
    Allows selective field output to minimize payload size.
    """
    default_fields = ['id', 'first_name', 'last_initial']
    optional_fields = ['full_name', 'email', 'classrooms', 'reading_groups', 'last_activity']
    
    @staticmethod
    def get_full_name(obj):
        """Get student's full name"""
        return obj.full_name
    
    @staticmethod
    def get_classrooms(obj):
        """Get student's classrooms (ID and name only)"""
        # Assumes classrooms are prefetched
        return [
            {'id': c.id, 'name': c.name}
            for c in obj.students_classrooms.all()
        ]
    
    @staticmethod
    def get_reading_groups(obj):
        """Get student's reading groups (ID and name only)"""
        # Assumes reading_groups are prefetched
        return [
            {'id': g.id, 'name': g.name}
            for c in obj.reading_groups.all()
        ]
    
    @staticmethod
    def get_last_activity(obj):
        """Get last log date"""
        if hasattr(obj, 'last_log_date') and obj.last_log_date:
            return obj.last_log_date.isoformat()
        return None


class LogSerializer(BaseSerializer):
    """
    Serializer for Reading Log data.
    Reduces payload by sending only needed fields.
    """
    default_fields = ['id', 'date', 'pages', 'minutes']
    optional_fields = ['title', 'author', 'rating', 'comments', 'student_id', 'student_name']
    
    @staticmethod
    def get_date(obj):
        """Format date as ISO string"""
        if hasattr(obj, 'date') and obj.date:
            return obj.date.isoformat()
        return None
    
    @staticmethod
    def get_student_name(obj):
        """Get student name if relation is loaded"""
        if hasattr(obj, 'student') and obj.student:
            return obj.student.full_name
        return None
    
    @staticmethod
    def get_rating(obj):
        """Format rating as float"""
        if hasattr(obj, 'rating') and obj.rating:
            return float(obj.rating)
        return None


class ClassroomSerializer(BaseSerializer):
    """Serializer for Classroom data"""
    default_fields = ['id', 'name']
    optional_fields = ['student_count', 'teachers', 'created_date']
    
    @staticmethod
    def get_student_count(obj):
        """Get count of students"""
        if hasattr(obj, 'student_count'):
            return obj.student_count
        return obj.students.count()
    
    @staticmethod
    def get_teachers(obj):
        """Get list of teacher names"""
        return [
            {'id': t.id, 'name': t.full_name}
            for t in obj.teachers.all()
        ]
    
    @staticmethod
    def get_created_date(obj):
        """Format created date"""
        if hasattr(obj, 'created_date') and obj.created_date:
            return obj.created_date.isoformat()
        return None


class ProgressSerializer(BaseSerializer):
    """
    Serializer for student progress data.
    Used in dashboard and analytics endpoints.
    """
    default_fields = ['id', 'name', 'total_pages', 'total_minutes']
    optional_fields = ['logs_count', 'avg_rating', 'daily_avg_pages', 'daily_avg_minutes',
                       'goal_progress', 'goal_status', 'reading_streak']
    
    @staticmethod
    def get_name(obj):
        """Get name from dict or object"""
        if isinstance(obj, dict):
            return obj.get('name')
        return getattr(obj, 'full_name', None) or getattr(obj, 'name', None)
    
    @staticmethod
    def get_total_pages(obj):
        """Get total pages"""
        if isinstance(obj, dict):
            return obj.get('total_pages', 0)
        return getattr(obj, 'total_pages', 0)
    
    @staticmethod
    def get_total_minutes(obj):
        """Get total minutes"""
        if isinstance(obj, dict):
            return obj.get('total_minutes', 0)
        return getattr(obj, 'total_minutes', 0)


class GoalSerializer(BaseSerializer):
    """Serializer for reading goals"""
    default_fields = ['id', 'type', 'value']
    optional_fields = ['student_id', 'student_name', 'start_date', 'end_date', 'progress']
    
    @staticmethod
    def get_student_name(obj):
        """Get student name"""
        if hasattr(obj, 'student') and obj.student:
            return obj.student.full_name
        return None
    
    @staticmethod
    def get_start_date(obj):
        """Get start date for total goals"""
        if hasattr(obj, 'start') and obj.start:
            return obj.start.isoformat()
        return None
    
    @staticmethod
    def get_end_date(obj):
        """Get end date for total goals"""
        if hasattr(obj, 'end') and obj.end:
            return obj.end.isoformat()
        return None


def serialize_queryset(queryset, serializer_class, fields=None, request=None):
    """
    Helper function to serialize a queryset with optional field selection from request.
    
    Args:
        queryset: Django QuerySet to serialize
        serializer_class: Serializer class to use
        fields: List of fields to include (default: from serializer)
        request: HTTP request object (to get fields from query params)
        
    Returns:
        list: Serialized data
    """
    # Allow fields to be specified via query param
    if request and not fields:
        fields_param = request.GET.get('fields', '')
        if fields_param:
            fields = [f.strip() for f in fields_param.split(',') if f.strip()]
    
    return serializer_class.serialize_many(queryset, fields=fields)


def get_requested_fields(request, default_fields=None):
    """
    Extract requested fields from query parameters.
    
    Args:
        request: HTTP request object
        default_fields: Default fields if none specified
        
    Returns:
        list or None: List of field names or None for defaults
    """
    if not request:
        return default_fields
    
    fields_param = request.GET.get('fields', '')
    if not fields_param:
        return default_fields
    
    return [f.strip() for f in fields_param.split(',') if f.strip()]


