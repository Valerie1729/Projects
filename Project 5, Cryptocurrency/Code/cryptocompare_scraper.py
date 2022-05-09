#
# Скрипт для загрузки/хранения криптовалютных данных  с cryptocompare.com.
#


# Импортируем библиотеки
import json
import requests
import datetime
import numpy as np
import pandas as pd

def clean_data(df):
    """
    Обрабатываем данные, полученные из API. Эта функция просто усредняет
    показатели для каждой криптовалюты на пяти биржах, которые мы
    выбрали для использования.

    Входные данные:
        df: данные из API (прямо из CSV, сохраненного после двойного цикла ниже)

    Возвращает:
        new_df: обработанный DF (только средние цены закрытия для каждой криптовалюты)
    """
    # Устанавливаем индекс.
    df.set_index('time', inplace=True)

    # Обрабатываем пустые значения.
    df.replace(0.0, np.nan, inplace=True)

    # Создаём новые показатели.
    df['volume'] = df['volumeto'] - df['volumefrom']
    df['fluctuation'] = (df['high']-df['low']) / (df['open'])
    df['relative_hl_close'] = (df['close']-df['low']) / (df['high']-df['low'])

    # Выбираем только важные столбцы.
    sub_df = df[['close','volume','fluctuation','relative_hl_close',
                 'exchange','fsym_tsym']]

    # Среднее для всех показателей по биржам.
    group_df = sub_df.groupby([sub_df.index,'fsym_tsym']).agg({'close':[np.nanmean],'volume':[np.nanmean],'fluctuation':[np.nanmean],'relative_hl_close':[np.nanmean]})

    # Отбрасываем ненужный label, создаём иерархическую метку для столбцов
    group_df.columns = group_df.columns.droplevel(level=1)
    new_df = group_df.unstack(level='fsym_tsym')

    return new_df

def construct_url(params):
    """
    Создаёи URL-адрес, связанный с вызовом API cryptocompare.com.

    Входные данные:
        params: (такие же как в pull_data ниже)

    Возвращает:
        url:URL для запроса
        sym_string: идентификатор криптовалюты (просто метка на потом)
        exchange: биржа
    """
    base_url = 'https://min-api.cryptocompare.com/data/histohour?'
    fsym, tsym = params['syms']
    agg = params['aggregate']
    lim = params['limit']
    exchange = params['exchange']

    ext_url = 'fsym=' + fsym + '&tsym=' + tsym + '&limit=' + lim + '&aggregate=' \
              + agg + '&e=' + exchange

    url = base_url + ext_url
    sym_string = fsym + '_' + tsym

    return url, sym_string, exchange

def dateparse(epoch_time):
    """
    Преобразование эпохи в человеческую дату (UTC).
    """
    return datetime.datetime.fromtimestamp(float(epoch_time))

def pull_data(params):
    """
    Вызывает API, используя URL-адрес, созданный с помощью конструктора_url, добавляет несколько дополнительных
    столбцов в качестве меток.

    Входные данные:
        params: параметры для передачи в запросе
            fsym: 'из' символ (символ криптовалюты)
            tsym: 'в' символ  (USD)
            limit: количество возвращаемых точек времени (max: 2000)
            e: биржа (Coinbase, Poloniex, и т.д. 

    Возвращает:
        data: dataframe, содержащий данные из вызова API
    """

    url, s, e = construct_url(params)

    response = requests.get(url)
    response.raise_for_status()         # Выводит ошибку, если неверный ответ.
    json_response = response.json()

    data = pd.DataFrame(json_response['Data'])
    data['fsym_tsym'] = s
    data['exchange'] = e

    return data

# ОСНОВНАЯ ЧАСТЬ КОДА: Для каждой биржи и пары символов получаем данные через API.
#
exchanges = ['COINBASE', 'POLONIEX', 'KRAKEN', 'BITSTAMP', 'BITFINEX']
sym_pairs = [('BTC','USD'),('ETH','USD'), ('LTC','USD'), ('DASH','USD'),
             ('XMR','USD')]

full_df = pd.DataFrame() # инициальизируем пустой датафрйем
for sp in sym_pairs:
    for exc in exchanges:
        request_dict = {'syms': sp, 'aggregate': '1', 'limit':'2000',
                        'exchange': exc}
        df = pull_data(request_dict)

        if full_df.empty:
            full_df = df
        else:
            full_df = pd.concat([full_df, df], axis=0)

full_df.to_csv('crypto_data_all.csv', index=False)