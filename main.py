from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
from collections import defaultdict
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 사용하기 위한 비밀 키 설정

# 기본 비밀번호 설정 (여기서는 'password'를 예시로 사용)
password_hash = generate_password_hash('asan1234..')

@app.route('/')
def index():
    # 로그인 여부 확인
    if 'logged_in' in session:
        return render_template('index.html')  # 로그인 성공 시 index.html 반환
    return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 리다이렉션

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if check_password_hash(password_hash, password):
            session['logged_in'] = True  # 로그인 성공 시 세션에 설정
            return redirect(url_for('index'))
        else:
            return '비밀번호가 잘못되었습니다.'
    return render_template('login.html')  # GET 요청 시 로그인 페이지 반환

@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # 세션에서 logged_in 제거
    return redirect(url_for('login'))  # 로그아웃 후 로그인 페이지로 리다이렉션

if __name__ == '__main__':
    app.run(debug=True)
    

# 근무자 리스트
employees = [
    "김상위", "김성배", "김태원", "류백렬", "정경해", "이재철", "장흥문", "류민희", "이재련", "이대호",
    "안진희", "박숙련", "홍용상", "김규표", "윤덕현", "김선영", "김정은", "유창훈", "정재호", "윤신교",
    "박인근", "조형우", "김형돈", "서세영", "천재경", "정혜현", "형재원", "신여경", "김성은", "김소연"
]

# 영어 요일 -> 한글 요일 매핑
english_to_korean_day = {
    'Monday': '월',
    'Tuesday': '화',
    'Wednesday': '수',
    'Thursday': '목',
    'Friday': '금',
    'Saturday': '토',
    'Sunday': '일'
}


# 스케줄 생성 함수
def generate_schedule(employees, unavailable_info, excluded_employees,
                      start_date):
    # 제외된 근무자 제거
    available_employees = [
        emp for emp in employees if emp not in excluded_employees
    ]

    # 첫 근무 배정을 랜덤화하기 위해 리스트를 섞음
    random.shuffle(available_employees)

    schedule = {}
    assigned_dates = {emp: None for emp in available_employees}  # 근무 일자 관리
    work_count = defaultdict(lambda: {
        "weekday": 0,
        "weekend": 0
    })  # 근무자별 주중/주말 근무 횟수

    if not start_date:
        start_date = datetime.now()  # 현재 날짜로 설정
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')

    end_date = start_date + timedelta(days=29)  # 한 달 동안의 스케줄 생성

    date = start_date

    while date <= end_date:
        day_of_week = date.strftime('%A')
        day_of_week_korean = english_to_korean_day[day_of_week]  # 한글 요일로 변환
        date_str = date.strftime('%Y-%m-%d')

        available_for_day = []

        # 각 근무자에 대해 근무 가능 여부를 체크
        for emp in available_employees:
            emp_unavail_days = unavailable_info.get(emp, {}).get(
                'unavailable_days', [])
            emp_unavail_dates = unavailable_info.get(emp, {}).get(
                'unavailable_dates', [])
            last_assigned_date = assigned_dates[emp]

            # 해당 요일과 날짜가 근무 불가 날짜에 해당하는지 체크
            if (day_of_week_korean not in emp_unavail_days
                    and date_str not in emp_unavail_dates):
                if last_assigned_date is None or (
                        date - last_assigned_date).days >= 3:  # 최소 3일 간격
                    available_for_day.append(emp)

        # 근무자 간의 근무 일수 차이를 최소화하기 위한 로직
        if available_for_day:
            # 주말이면 2일 근무로 계산
            if day_of_week in ['Saturday', 'Sunday']:
                chosen_employees = select_employees_equally(available_for_day,
                                                            work_count,
                                                            is_weekend=True)
                for emp in chosen_employees:
                    work_count[emp]['weekend'] += 2
            else:  # 주중이면 1일 근무로 계산
                chosen_employees = select_employees_equally(available_for_day,
                                                            work_count,
                                                            is_weekend=False)
                for emp in chosen_employees:
                    work_count[emp]['weekday'] += 1

            schedule[date_str] = chosen_employees

            # 배정된 사람의 마지막 근무 일자를 갱신
            for emp in chosen_employees:
                assigned_dates[emp] = date

        date += timedelta(days=1)

    return schedule


# 가중치 기반으로 근무자를 선택하되, 랜덤하게 배정하는 함수
def select_employees_equally(available_employees, work_count, is_weekend):
    # 현재 주중/주말 근무 횟수를 기준으로 선택
    if is_weekend:
        # 주말인 경우
        employee_weights = [
            (emp, work_count[emp]['weekend'] * 2 + work_count[emp]['weekday'])
            for emp in available_employees
        ]
    else:
        # 주중인 경우
        employee_weights = [
            (emp, work_count[emp]['weekday'] + work_count[emp]['weekend'] * 2)
            for emp in available_employees
        ]

    # 가중치가 낮은 순서대로 정렬하여 랜덤으로 선택
    employee_weights.sort(key=lambda x: x[1])

    # 상위 5명 중에서 랜덤으로 3명 선택 (최대 3명)
    selected_employees = random.sample(
        [emp for emp, _ in employee_weights[:min(5, len(employee_weights))]],
        min(3, len(employee_weights)))

    return selected_employees


# 메인 페이지 라우팅
@app.route('/')
def index():
    return render_template('index.html', employees=employees)


# 스케줄 생성 API
@app.route('/generate_schedule', methods=['POST'])
def generate_schedule_api():
    data = request.json  # 프론트엔드에서 전송한 데이터를 받음
    unavailable_info = data['unavailable_info']
    excluded_employees = data['excluded_employees']
    start_date = data['start_date']

    # 모든 입력이 공란일 경우 현재 날짜로 시작
    if not start_date and not excluded_employees and all(
            not unavailable_info.get(emp, {}).get('unavailable_days', [])
            and not unavailable_info.get(emp, {}).get('unavailable_dates', [])
            for emp in unavailable_info):
        start_date = datetime.now().strftime('%Y-%m-%d')

    # 스케줄 생성 함수 호출
    schedule = generate_schedule(employees, unavailable_info,
                                 excluded_employees, start_date)

    return jsonify(schedule)


#if __name__ == "__main__":
 #   app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # 환경 변수 PORT 사용, 없으면 8080 사용
    app.run(host='0.0.0.0', port=port)
