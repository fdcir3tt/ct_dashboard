from datetime import datetime,timezone,timedelta

def date_interval(reference_date:datetime,days:int)->tuple[datetime,datetime]:
    """
    
    """
    time_difference = abs(days)
    
    if days <0:
        start = reference_date - timedelta(days=time_difference)
        end = reference_date
    else:
        start = reference_date
        end = reference_date + timedelta(days=time_difference)
    interval = (start,end)
    return interval

def date(date_str:str)->datetime:
    if date_str=="today":
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str=="yesterday":
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)-timedelta(days=1)
    year,month,day = date_str.split('-')
    
    return datetime(int(year),int(month),int(day),tzinfo=timezone.utc)

def time_period(start_date: str, end_date: str) -> list[datetime]:
    """
    Genera una lista de fechas en el periodo designado

    Parametros:
    - start_date: str , Fecha inicio del periodo
    - end_date: str , Fecha fin del periodo
    Regresa:
    - dates:list[datetime], Lista de fechas entre 'start_date' y 'end_date'

    """
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = date(start_date)

    while current <= date(end_date):
        dates.append(current)
        current += timedelta(days=1)

    return dates