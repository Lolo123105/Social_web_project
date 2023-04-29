import datetime as dt


def year(request):
    """Добавляет переменную с текущим годом."""
    today = dt.datetime.today()
    return {
        'year': today.year
    }
