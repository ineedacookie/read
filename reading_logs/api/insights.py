"""
Classroom Insights API Endpoints
Handles insight sharing and collaboration features.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
import logging
import hashlib
import json

from reading_logs.models import ClassroomInsight, InsightHelpful
from read.utils import success_response, error_response
from read.utils.decorators import ajax_login_required

logger = logging.getLogger('reading_logs.api')


@login_required
def classroom_insights_view(request):
    """Classroom insights sharing page for teachers"""
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access classroom insights")
    
    return render(request, 'general/classroom_insights.html')


@ajax_login_required
def api_classroom_insights(request):
    """API for fetching shared classroom insights"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method != "GET":
        return error_response("Method not allowed", status=405)
    
    try:
        # Get insights for school
        insights = ClassroomInsight.objects.filter(
            school=request.user.school,
            is_approved=True
        ).order_by('-helpful_count', '-created_date')
        
        # Apply category filter
        category = request.GET.get('category')
        if category:
            insights = insights.filter(category=category)
        
        # Limit results
        insights = insights[:50]
        
        insights_data = [
            {
                'id': insight.id,
                'title': insight.title,
                'description': insight.description,
                'tips': insight.implementation_tips,
                'category': insight.category,
                'metric': insight.success_metric,
                'helpful_count': insight.helpful_count,
                'created_at': insight.created_date.isoformat(),
                'allow_contact': insight.allow_contact,
                'is_featured': insight.is_featured
            }
            for insight in insights
        ]
        
        total_count = ClassroomInsight.objects.filter(
            school=request.user.school,
            is_approved=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'insights': insights_data,
                'total_insights': total_count
            }
        })
        
    except Exception as e:
        return error_response(f"Failed to load insights: {str(e)}", status=500)


@login_required
def api_share_insight(request):
    """API for sharing a new classroom insight"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method != "POST":
        return error_response("Method not allowed", status=405)
    
    try:
        # Get form data
        category = request.POST.get('category')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        tips = request.POST.get('tips', '').strip()
        metric = request.POST.get('metric')
        allow_contact = request.POST.get('allow_contact') == 'on'
        
        # Validation
        if not category or not title or not description:
            return error_response("Category, title, and description are required", status=400)
        
        if len(title) > 100:
            return error_response("Title too long (max 100 characters)", status=400)
        
        if len(description) > 1000:
            return error_response("Description too long (max 1000 characters)", status=400)
        
        if tips and len(tips) > 500:
            return error_response("Tips too long (max 500 characters)", status=400)
        
        # Create teacher hash for anonymity
        teacher_hash = hashlib.sha256(
            f"teacher_{request.user.id}_{request.user.school.id}".encode()
        ).hexdigest()
        
        # Create insight
        insight = ClassroomInsight.objects.create(
            school=request.user.school,
            teacher_hash=teacher_hash,
            category=category,
            title=title,
            description=description,
            implementation_tips=tips if tips else None,
            success_metric=metric if metric else None,
            allow_contact=allow_contact
        )
        
        return success_response("Your insight has been shared successfully!", data={'insight_id': insight.id})
        
    except Exception as e:
        return error_response(f"Failed to share insight: {str(e)}", status=500)


@login_required
def api_mark_helpful(request):
    """API for marking an insight as helpful"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method != "POST":
        return error_response("Method not allowed", status=405)
    
    try:
        data = json.loads(request.body)
        insight_id = data.get('insight_id')
        
        if not insight_id:
            return error_response("Insight ID is required", status=400)
        
        # Get the insight
        try:
            insight = ClassroomInsight.objects.get(
                id=insight_id,
                school=request.user.school,
                is_approved=True
            )
        except ClassroomInsight.DoesNotExist:
            return error_response("Insight not found", status=404)
        
        # Create teacher hash
        teacher_hash = hashlib.sha256(
            f"teacher_{request.user.id}_{request.user.school.id}".encode()
        ).hexdigest()
        
        # Check if already marked helpful
        if InsightHelpful.objects.filter(insight=insight, teacher_hash=teacher_hash).exists():
            return error_response("You have already marked this insight as helpful", status=400)
        
        # Create helpful vote
        InsightHelpful.objects.create(insight=insight, teacher_hash=teacher_hash)
        
        # Update helpful count
        insight.helpful_count = insight.helpful_votes.count()
        insight.save(update_fields=['helpful_count'])
        
        return success_response("Marked as helpful successfully")
        
    except Exception as e:
        return error_response(f"Failed to mark as helpful: {str(e)}", status=500)


# Comparison API
@ajax_login_required
def api_classroom_comparison(request):
    """
    API for anonymized classroom performance comparison.
    OPTIMIZED: Batch queries all classroom logs in one query.
    """
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method != "GET":
        return error_response("Method not allowed", status=405)
    
    try:
        from reading_logs.models import Log
        from datetime import date, timedelta
        
        # Get date range (default to current month)
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
        
        if request.GET.get('start_date'):
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        if request.GET.get('end_date'):
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # OPTIMIZED: Prefetch students and batch query all logs
        classrooms = Classroom.objects.filter(
            school=request.user.school
        ).prefetch_related('students').annotate(student_count=Count('students'))
        
        my_classrooms = list(classrooms.filter(teachers=request.user)) if request.user.user_type == 'teacher' else []
        
        # CRITICAL: Batch query ALL logs for ALL classrooms
        all_classroom_logs = Log.objects.filter(
            student__students_classrooms__school=request.user.school,
            date__range=(start_date, end_date)
        ).values('student__students_classrooms__id', 'pages', 'minutes', 'rating')
        
        # Group logs by classroom_id
        logs_by_classroom = {}
        for log in all_classroom_logs:
            cid = log['student__students_classrooms__id']
            logs_by_classroom.setdefault(cid, []).append(log)
        
        # Process classrooms
        anonymous_classrooms = []
        my_classroom_data = None
        
        for classroom in classrooms:
            classroom_logs = logs_by_classroom.get(classroom.id, [])
            
            if classroom.student_count == 0:
                continue
            
            total_pages = sum(log['pages'] or 0 for log in classroom_logs)
            pages_per_student = total_pages / classroom.student_count
            minutes_per_student = sum(log['minutes'] or 0 for log in classroom_logs) / classroom.student_count
            ratings = [log['rating'] for log in classroom_logs if log['rating']]
            
            classroom_data = {
                'pages_per_student': round(pages_per_student, 1),
                'minutes_per_student': round(minutes_per_student, 1),
                'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                'student_count': classroom.student_count,
                'is_current_user': request.user.user_type == 'teacher' and classroom in my_classrooms
            }
            
            if classroom_data['is_current_user']:
                my_classroom_data = classroom_data.copy()
            
            anonymous_classrooms.append(classroom_data)
        
        # Calculate school averages and rankings
        sorted_classrooms = sorted(anonymous_classrooms, key=lambda x: x['pages_per_student'], reverse=True)
        
        my_rank = next(
            (i + 1 for i, c in enumerate(sorted_classrooms) if c.get('is_current_user')),
            len(sorted_classrooms)
        )
        
        if my_classroom_data:
            my_classroom_data['rank'] = my_rank
        
        return JsonResponse({
            'success': True,
            'data': {
                'my_classroom': my_classroom_data or {'pages_per_student': 0, 'rank': len(sorted_classrooms)},
                'school_data': {
                    'avg_pages_per_student': round(sum(c['pages_per_student'] for c in anonymous_classrooms) / len(anonymous_classrooms), 1) if anonymous_classrooms else 0,
                    'top_pages_per_student': sorted_classrooms[0]['pages_per_student'] if sorted_classrooms else 0,
                    'total_classrooms': len(anonymous_classrooms)
                },
                'anonymous_classrooms': anonymous_classrooms[:10]
            }
        })
        
    except Exception as e:
        return error_response(f"Failed to load comparison data: {str(e)}", status=500)

