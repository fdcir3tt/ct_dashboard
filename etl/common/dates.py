from datetime import datetime,timezone,timedelta

def date_interval(reference_date:datetime,days:int)->tuple[datetime,datetime]:
    """
    Genera un intervalo de fechas a partir de una fecha de referencia.

    Parameters
    ----------
    reference_date : datetime
        Fecha base a partir de la cual se calcula el intervalo.
    days : int
        Número de días para construir el intervalo. Si es negativo,
        el intervalo va hacia atrás en el tiempo; si es positivo,
        va hacia adelante.

    Returns
    -------
    tuple of datetime
        Tupla (start, end) que representa el intervalo de fechas.

    Notes
    -----
    El valor absoluto de `days` determina la duración del intervalo,
    mientras que el signo define la dirección del mismo.
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
    """
    Convierte una cadena de texto en un objeto datetime con zona horaria UTC.

    Parameters
    ----------
    date_str : str
        Fecha en formato 'YYYY-MM-DD' o valores especiales:
        - "today": retorna el inicio del día actual en UTC
        - "yesterday": retorna el inicio del día anterior en UTC

    Returns
    -------
    datetime
        Objeto datetime correspondiente a la fecha especificada en UTC.

    Raises
    ------
    ValueError
        Si el formato de la fecha no es válido.

    Notes
    -----
    Las fechas "today" y "yesterday" se normalizan al inicio del día (00:00:00).
    """
    if date_str=="today":
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str=="yesterday":
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)-timedelta(days=1)
    year,month,day = date_str.split('-')
    
    return datetime(int(year),int(month),int(day),tzinfo=timezone.utc)

def time_period(start_date: str, end_date: str) -> list[datetime]:
    """
    Genera una lista de fechas entre dos fechas incluidas.

    Parameters
    ----------
    start_date : str
        Fecha de inicio en formato 'YYYY-MM-DD' o formato aceptado por `date()`.
    end_date : str
        Fecha final en formato 'YYYY-MM-DD' o formato aceptado por `date()`.

    Returns
    -------
    list of datetime
        Lista de objetos datetime desde `start_date` hasta `end_date`
        (ambas fechas incluidas), con incremento diario.

    Raises
    ------
    ValueError
        Si la fecha inicial es posterior a la fecha final.

    Notes
    -----
    Internamente utiliza la función `date()` para normalizar las fechas
    y avanza en incrementos de un día (`timedelta(days=1)`).
    """
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = date(start_date)

    while current <= date(end_date):
        dates.append(current)
        current += timedelta(days=1)

    return dates