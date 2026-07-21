from django.utils import timezone

def record_user_activity(user):
    """
    记录用户当天活跃事实
    并根据提问次数和活跃天数动态计算 frequency（活跃度等级）
    """
    try:
        persona = user.persona
    except Exception:
        # 兼容旧用户没有画像的情况
        from chunker_api.models import UserPersona
        persona = UserPersona.objects.create(
            user=user,
            role='enterprise' if user.user_type == 'enterprise' else 'local'
        )
    today = timezone.now().date()

    persona.total_questions += 1

    if persona.last_active_date != today:
        persona.active_days += 1
        persona.last_active_date = today

    # 动态计算活跃度等级 (frequency)
    if persona.active_days >= 10 or persona.total_questions >= 50:
        persona.frequency = 'high'
    elif persona.active_days >= 3 or persona.total_questions >= 15:
        persona.frequency = 'normal'
    else:
        persona.frequency = 'new'

    persona.save(update_fields=[
        'total_questions',
        'active_days',
        'last_active_date',
        'frequency',
        'updated_at'
    ])
