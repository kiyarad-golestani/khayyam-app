from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import jdatetime
import os

from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import jdatetime

def haversine(lat1, lon1, lat2, lon2):
    # محاسبه فاصله بین دو نقطه جغرافیایی به کیلومتر
    R = 6371  # شعاع زمین به کیلومتر
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)*2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)*2
    c = 2 * asin(sqrt(a))
    return R * c * 1000  # به متر

app = Flask(__name__)
app.secret_key = 'mysecretkey' # برای نگهداری session

# مسیر به فایل اکسل
EXCEL_FILE = 'Khayyam.xlsx'

# صفحه ورود
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # گرفتن مقدار از فرم و حذف فاصله
        username = str(request.form.get('username', '')).strip()
        password = str(request.form.get('password', '')).strip()

        # خواندن شیت users از فایل Excel
        try:
            df_users = pd.read_excel(EXCEL_FILE, sheet_name='users')
        except Exception as e:
            return f"خطا در خواندن فایل Excel: {e}"

        # مطمئن شدن از وجود ستون‌ها
        if 'Userv' not in df_users.columns or 'Passv' not in df_users.columns:
            return "ستون‌های لازم در شیت users پیدا نشدند."

        # پاک‌سازی: تبدیل به رشته و حذف فاصله
        df_users['Userv'] = df_users['Userv'].astype(str).str.strip()
        df_users['Passv'] = df_users['Passv'].astype(str).str.strip()

        # فیلتر کردن کاربران مطابق نام کاربری و رمز
        user_row = df_users[
            (df_users['Userv'] == username) & (df_users['Passv'] == password)
        ]

        if not user_row.empty:
            session['codev'] = str(user_row.iloc[0]['Codev'])
            session['namev'] = str(user_row.iloc[0]['Namev'])
            return redirect(url_for('welcome'))
        else:
            return render_template('login.html', error='نام کاربری یا رمز عبور اشتباه است.')

    return render_template('login.html')


# صفحه خوش‌آمدگویی بعد از ورود موفق

@app.route('/welcome')
def welcome():
    if 'codev' not in session:
            return redirect(url_for('login'))
    return render_template('welcome.html', name=session['namev'])   



@app.route('/report_items', methods=['GET', 'POST'])
def report_items():
    if 'codev' not in session:
        return redirect(url_for('login'))

    namev = session['namev']
    codev = str(session['codev']).strip()

    if request.method == 'POST':
        # دریافت تاریخ و تبدیل به عدد
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))

        # خواندن داده‌ها از اکسل
        df_kala = pd.read_excel(EXCEL_FILE, sheet_name='kala')
        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')

        # پاک‌سازی فیلدها
        df_kala['Namek'] = df_kala['Namek'].astype(str).str.strip()
        df_forosh['Namek'] = df_forosh['Namek'].astype(str).str.strip()
        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')
        df_forosh['Pkol'] = pd.to_numeric(df_forosh['Pkol'], errors='coerce').fillna(0)

        # فیلتر بازاریاب + بازه تاریخ
        df_filtered = df_forosh[
            (df_forosh['Codev'] == codev) &
            (df_forosh['DateF'] >= from_date) &
            (df_forosh['DateF'] <= to_date)
        ]

        # بررسی اینکه فروش وجود داشته یا نه
        if df_filtered.empty:
            return render_template('welcome.html', name=namev, sold=None, unsold=None, message="فروشی در این بازه وجود ندارد.")

        # گروه‌بندی فروش بر اساس نام کالا
        df_grouped = df_filtered.groupby('Namek')['Pkol'].sum().reset_index()
        df_grouped = df_grouped.sort_values(by='Pkol', ascending=False)

        total_sales = df_grouped['Pkol'].sum()
        sold_list = []
        for _, row in df_grouped.iterrows():
            percent = round((row['Pkol'] / total_sales) * 100, 2) if total_sales else 0
            sold_list.append({
                'Namek': row['Namek'],
                'total': int(row['Pkol']),
                'percent': percent
            })

        # کالاهای نفروخته‌شده
        sold_names = df_grouped['Namek'].tolist()
        all_kala = df_kala['Namek'].tolist()
        unsold = [k for k in all_kala if k not in sold_names]

        #return render_template('welcome.html', name=namev, sold=sold_list, unsold=unsold)
        return render_template('report_items.html', name=namev, sold=sold_list, unsold=unsold) 
    #return render_template('welcome.html', name=namev)
    return render_template('report_items.html', name=namev)
    
@app.route('/report_customers', methods=['GET', 'POST'])

def report_customers():
    if 'codev' not in session:
        return redirect(url_for('login'))

    namev = session['namev']
    codev = str(session['codev']).strip()

    if request.method == 'POST':
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))

        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')
        df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')

        # پاک‌سازی
        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['Codec'] = df_forosh['Codec'].astype(str).str.strip()
        df_forosh['Pkol'] = pd.to_numeric(df_forosh['Pkol'], errors='coerce').fillna(0)
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')

        df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
        df_customer['Codec'] = df_customer['Codec'].astype(str).str.strip()
        df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()

        # مشتری‌های این بازاریاب
        df_my_customers = df_customer[df_customer['Codev'] == codev]

        # فروش‌های بازاریاب در بازه
        df_filtered = df_forosh[
            (df_forosh['Codev'] == codev) &
            (df_forosh['DateF'] >= from_date) &
            (df_forosh['DateF'] <= to_date)
        ]

        # گروه‌بندی مبلغ خرید هر مشتری
        df_grouped = df_filtered.groupby('Codec')['Pkol'].sum().reset_index()
        df_grouped['Pkol'] = df_grouped['Pkol'].astype(int)

        total_sales = df_grouped['Pkol'].sum()

        # اتصال با نام مشتری
        df_merged = pd.merge(df_grouped, df_my_customers, on='Codec', how='left')

        buyer_list = []
        for _, row in df_merged.iterrows():
            percent = round((row['Pkol'] / total_sales) * 100, 2) if total_sales else 0
            buyer_list.append({
                'Namec': row['Namec'],
                'total': row['Pkol'],
                'percent': percent
            })

        # مشتری‌هایی که خرید نکردند
        all_codecs = df_my_customers['Codec'].tolist()
        buyer_codecs = df_grouped['Codec'].tolist()
        not_buyer_list = df_my_customers[~df_my_customers['Codec'].isin(buyer_codecs)]['Namec'].tolist()

        return render_template('report_customers.html', name=namev, buyers=buyer_list, not_buyers=not_buyer_list)

    return render_template('report_customers.html', name=namev)    

@app.route('/report_kala_customers', methods=['GET', 'POST'])
def report_kala_customers():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']

    df_kala = pd.read_excel(EXCEL_FILE, sheet_name='kala')
    df_kala['Codek'] = df_kala['Codek'].astype(str).str.strip()
    df_kala['Namek'] = df_kala['Namek'].astype(str).str.strip()
    kala_list = df_kala.to_dict(orient='records')

    if request.method == 'POST':
        selected_codek = request.form['codek'].strip()
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))

        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')
        df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')

        # پاک‌سازی
        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['Codec'] = df_forosh['Codec'].astype(str).str.strip()
        df_forosh['Codek'] = df_forosh['Codek'].astype(str).str.strip()
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')

        df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
        df_customer['Codec'] = df_customer['Codec'].astype(str).str.strip()
        df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()

        # مشتری‌های این بازاریاب
        df_my_customers = df_customer[df_customer['Codev'] == codev]

        # فیلتر فروش‌ها
        df_filtered = df_forosh[
            (df_forosh['Codev'] == codev) &
            (df_forosh['Codek'] == selected_codek) &
            (df_forosh['DateF'] >= from_date) &
            (df_forosh['DateF'] <= to_date)
        ]

        # مشتریانی که این کالا را خریده‌اند
        buyers = df_filtered['Codec'].unique().tolist()
        df_bought = df_my_customers[df_my_customers['Codec'].isin(buyers)]
        df_not_bought = df_my_customers[~df_my_customers['Codec'].isin(buyers)]

        return render_template('report_kala_customers.html', name=namev, kala_list=kala_list, bought=df_bought['Namec'].tolist(), not_bought=df_not_bought['Namec'].tolist())

    return render_template('report_kala_customers.html', name=namev, kala_list=kala_list)

@app.route('/report_customer_kala', methods=['GET', 'POST'])
def report_customer_kala():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']

    # دریافت مشتری‌های بازاریاب لاگین‌شده
    df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')
    df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
    df_customer['Codec'] = df_customer['Codec'].astype(str).str.strip()
    df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()

    df_my_customers = df_customer[df_customer['Codev'] == codev]
    customer_list = df_my_customers.to_dict(orient='records')

    if request.method == 'POST':
        selected_codec = request.form['codec'].strip()
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))

        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')
        df_kala = pd.read_excel(EXCEL_FILE, sheet_name='kala')

        # پاک‌سازی
        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['Codec'] = df_forosh['Codec'].astype(str).str.strip()
        df_forosh['Codek'] = df_forosh['Codek'].astype(str).str.strip()
        df_forosh['Namek'] = df_forosh['Namek'].astype(str).str.strip()
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')

        df_kala['Codek'] = df_kala['Codek'].astype(str).str.strip()
        df_kala['Namek'] = df_kala['Namek'].astype(str).str.strip()

        # فیلتر فروش‌های مشتری در بازه
        df_filtered = df_forosh[
            (df_forosh['Codev'] == codev) &
            (df_forosh['Codec'] == selected_codec) &
            (df_forosh['DateF'] >= from_date) &
            (df_forosh['DateF'] <= to_date)
        ]

        bought_names = df_filtered['Namek'].unique().tolist()
        all_names = df_kala['Namek'].tolist()
        not_bought_names = [k for k in all_names if k not in bought_names]

        return render_template('report_customer_kala.html', name=namev, customer_list=customer_list, bought=bought_names, not_bought=not_bought_names)

    return render_template('report_customer_kala.html', name=namev, customer_list=customer_list)

@app.route('/report_sahmiye', methods=['GET', 'POST'])
def report_sahmiye():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']

    if request.method == 'POST':
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))

        df_sahmiye = pd.read_excel(EXCEL_FILE, sheet_name='sahmiye')
        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')

        # پاک‌سازی
        df_sahmiye['Codev'] = df_sahmiye['Codev'].astype(str).str.strip()
        df_sahmiye['Codek'] = df_sahmiye['Codek'].astype(str).str.strip()
        df_sahmiye['Namek'] = df_sahmiye['Namek'].astype(str).str.strip()
        df_sahmiye['Nums'] = pd.to_numeric(df_sahmiye['Nums'], errors='coerce').fillna(0)

        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['Codek'] = df_forosh['Codek'].astype(str).str.strip()
        df_forosh['Sumk'] = pd.to_numeric(df_forosh['Sumk'], errors='coerce').fillna(0)
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')

        # فقط سهمیه‌های بازاریاب جاری
        df_my_sahmiye = df_sahmiye[df_sahmiye['Codev'] == codev]

        # فروش‌های بازاریاب در بازه تاریخ
        df_filtered = df_forosh[
            (df_forosh['Codev'] == codev) &
            (df_forosh['DateF'] >= from_date) &
            (df_forosh['DateF'] <= to_date)
        ]

        # جمع فروش کالاها
        df_sales = df_filtered.groupby('Codek')['Sumk'].sum().reset_index()

        # اتصال فروش با سهمیه‌ها
        df_merged = pd.merge(df_my_sahmiye, df_sales, on='Codek', how='left')
        df_merged['Sumk'] = df_merged['Sumk'].fillna(0)
        df_merged['percent'] = round((df_merged['Sumk'] / df_merged['Nums']) * 100, 2)

        # تهیه خروجی
        result = []
        for _, row in df_merged.iterrows():
            result.append({
                'Namek': row['Namek'],
                'sahmiye': int(row['Nums']),
                'sold': int(row['Sumk']),
                'percent': row['percent']
            })

        return render_template('report_sahmiye.html', name=namev, result=result)

    return render_template('report_sahmiye.html', name=namev)
 
@app.route('/catalog', methods=['GET', 'POST'])
def catalog():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']

    # تابع مطمئن تمیز کردن Codek
    def clean_codek(x):
        if pd.notnull(x) and str(x).strip() != '':
            return str(int(float(x)))
        else:
            return ''

    # 1️⃣ خواندن اکسل کالاها
    df_kala = pd.read_excel(EXCEL_FILE, sheet_name='kala')
    df_kala['Codek'] = df_kala['Codek'].apply(clean_codek)
    df_kala['Namek'] = df_kala['Namek'].astype(str).str.strip()
    df_kala['Brand'] = df_kala['Brand'].astype(str).str.strip()
    df_kala['info'] = df_kala['info'].astype(str).str.strip()
    df_kala['Radif'] = pd.to_numeric(df_kala['Radif'], errors='coerce').fillna(0).astype(int)
    df_kala = df_kala.sort_values(by='Radif')

    brands = df_kala['Brand'].unique()

    # 2️⃣ خواندن مشتریان بازاریاب
    df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')
    df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
    df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()
    df_my_customers = df_customer[df_customer['Codev'] == codev]
    customer_names = df_my_customers['Namec'].tolist()
    
    df_filtered_brand=df_kala
    
    result = []
    if request.method == 'POST':
        from_date = request.form['from_date'].replace('/', '')
        to_date = request.form['to_date'].replace('/', '')
        customer = request.form['customer'].strip()
        #selected_brand = request.form['brand'].strip()

        # 3️⃣ خواندن فروش
        df_forosh = pd.read_excel(EXCEL_FILE, sheet_name='forosh')
        df_forosh['Codev'] = df_forosh['Codev'].astype(str).str.strip()
        df_forosh['Codec'] = df_forosh['Codec'].astype(str).str.strip()
        df_forosh['Codek'] = df_forosh['Codek'].apply(clean_codek)
        df_forosh['Namek'] = df_forosh['Namek'].astype(str).str.strip()
        df_forosh['Sumk'] = pd.to_numeric(df_forosh['Sumk'], errors='coerce').fillna(0)
        df_forosh['DateF'] = pd.to_numeric(df_forosh['DateF'], errors='coerce')

        # 4️⃣ فیلتر فروش مشتری و تاریخ
        df_filtered = df_forosh[
            (df_forosh['Codec'] == customer) &
            (df_forosh['DateF'] >= int(from_date)) &
            (df_forosh['DateF'] <= int(to_date))
        ]

        # 5️⃣ خلاصه فروش کالاها
        df_sales = df_filtered.groupby('Codek').agg({'Sumk': 'sum', 'DateF': 'max'}).reset_index()
        df_sales['Codek'] = df_sales['Codek'].apply(clean_codek)

        # 6️⃣ فیلتر برند
        #if selected_brand == 'all':
        #    dFf_filtered_brand = df_kala
        #else:
        #    df_filtered_brand = df_kala[df_kala['Brand'] == selected_brand]
        
        df_filtered_brand = df_kala
        
        # 7️⃣ Merge کالاها با فروش
        df_merged = pd.merge(df_filtered_brand, df_sales, on='Codek', how='left')
        df_merged['Codek'] = df_merged['Codek'].apply(clean_codek)
        df_merged['Sumk'] = df_merged['Sumk'].fillna(0).astype(int)
        df_merged['DateF'] = df_merged['DateF'].fillna(0).astype(int)

        images_folder = os.path.join(app.root_path, 'static', 'images')

        result = []
        for _, row in df_merged.iterrows():
            codek = row['Codek']
            image_filename = f"{codek}.jpg"
            image_path = os.path.join(images_folder, image_filename)

            if not os.path.isfile(image_path):
                image_filename = 'default.jpg'

            result.append({
                'Codek': codek,
                'Namek': row['Namek'],
                'Brand': row['Brand'],
                'info': row['info'],
                'image': image_filename,
                'purchased': row['Sumk'] > 0,
                'last_date': row['DateF'] if row['Sumk'] > 0 else None,
                'last_qty': row['Sumk'] if row['Sumk'] > 0 else None
            })
    print(result[:2])
    
    return render_template('catalog.html', name=namev, brands=brands, customer_names=customer_names, result=result)
    
@app.route('/presence', methods=['GET', 'POST'])
def presence():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']

    df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')
    df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
    df_customer['Codec'] = df_customer['Codec'].astype(str).str.strip()
    df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()

    my_customers = df_customer[df_customer['Codev'] == codev]

    if request.method == 'POST':
        codec = request.form['codec']
        lat = float(request.form['lat'])
        lon = float(request.form['lon'])

        row = df_customer[df_customer['Codec'] == codec].iloc[0]
        latc = row.get('LatC')
        lonc = row.get('LonC')

        if pd.isna(latc) or pd.isna(lonc):
            df_customer.loc[df_customer['Codec'] == codec, 'LatC'] = lat
            df_customer.loc[df_customer['Codec'] == codec, 'LonC'] = lon
            with pd.ExcelWriter(EXCEL_FILE, mode='a', if_sheet_exists='replace') as writer:
                df_customer.to_excel(writer, sheet_name='customer', index=False)
            msg = 'لوکیشن مشتری ثبت شد.'
        else:
            distance = haversine(lat, lon, float(latc), float(lonc))
            if distance <= 40:
                df_hozur = pd.read_excel(EXCEL_FILE, sheet_name='hozur')
                now = jdatetime.date.today().strftime('%Y%m%d')
                t = datetime.now().strftime('%H:%M')
                df_hozur.loc[len(df_hozur.index)] = [codev, codec, row['Namec'], now, t]
                with pd.ExcelWriter(EXCEL_FILE, mode='a', if_sheet_exists='replace') as writer:
                    df_hozur.to_excel(writer, sheet_name='hozur', index=False)
                msg = f'حضور شما با موفقیت ثبت شد. فاصله: {int(distance)} متر'
            else:
                msg = f'شما در نزدیکی مشتری نیستید. فاصله: {int(distance)} متر'

        return render_template('presence.html', name=namev, customers=my_customers.to_dict(orient='records'), msg=msg)

    return render_template('presence.html', name=namev, customers=my_customers.to_dict(orient='records'))

@app.route('/hozur_report', methods=['GET', 'POST'])
def hozur_report():
    if 'codev' not in session:
        return redirect(url_for('login'))

    codev = str(session['codev']).strip()
    namev = session['namev']
    weeks = []

    if request.method == 'POST':
        from_date = int(request.form['from_date'].replace('/', ''))
        to_date = int(request.form['to_date'].replace('/', ''))
        
        start = jdatetime.date.fromgregorian(day=1, month=1, year=2000)
        try:
            start = jdatetime.datetime.strptime(str(from_date), '%Y%m%d').date()
            end = jdatetime.datetime.strptime(str(to_date), '%Y%m%d').date()
        except:
            return "تاریخ نامعتبر است."

        # شروع از شنبه هفته
        delta = jdatetime.timedelta(days=start.weekday())  # چند روز از شنبه گذشته
        first_saturday = start - delta

        while first_saturday <= end:
            week_start = first_saturday
            week_end = week_start + jdatetime.timedelta(days=6)
            if week_end > end:
                week_end = end
            weeks.append((week_start.strftime('%Y%m%d'), week_end.strftime('%Y%m%d')))
            first_saturday += jdatetime.timedelta(days=7)

        df_customer = pd.read_excel(EXCEL_FILE, sheet_name='customer')
        df_customer['Codev'] = df_customer['Codev'].astype(str).str.strip()
        df_customer['Codec'] = df_customer['Codec'].astype(str).str.strip()
        df_customer['Namec'] = df_customer['Namec'].astype(str).str.strip()
        my_customers = df_customer[df_customer['Codev'] == codev]

        df_hozur = pd.read_excel(EXCEL_FILE, sheet_name='hozur')
        df_hozur['Codev'] = df_hozur['Codev'].astype(str).str.strip()
        df_hozur['Codec'] = df_hozur['Codec'].astype(str).str.strip()
        df_hozur['Dateh'] = df_hozur['Dateh'].astype(str).str.strip()

        report = []

        for week_start, week_end in weeks:
            rows = []
            for _, row in my_customers.iterrows():
                codec = row['Codec']
                namec = row['Namec']
                visited = df_hozur[
                    (df_hozur['Codev'] == codev) &
                    (df_hozur['Codec'] == codec) &
                    (df_hozur['Dateh'] >= week_start) &
                    (df_hozur['Dateh'] <= week_end)
                ]
                status = '✅ حضور داشته' if not visited.empty else '❌ حضور نداشته'
                rows.append({'Codec': codec, 'Namec': namec, 'Status': status})
            report.append({'range': f"{week_start} تا {week_end}", 'rows': rows})

        return render_template('hozur_report.html', name=namev, report=report)

    return render_template('hozur_report.html', name=namev)

    
# خروج از حساب کاربری
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)