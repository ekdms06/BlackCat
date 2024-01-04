from flask import Flask, render_template, Response,request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import cv2
import mediapipe as mp
import os
import time
import threading


from models import db 
from flask import flash
from functools import wraps
from twilio.rest import Client
from flask_login import login_required 
from plyer import notification




link_dir = os.path.join(os.path.dirname(__file__), 'link')

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = '50089e690e2f6c591ec61974bdd88464' 
db = SQLAlchemy(app)


def send_sms(to, message):
    account_sid = 'ACd3835133a1fd153438c5f47e9a472de4'
    auth_token = 'b5dd505d11410caef931b79fb87f2cca'
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=message,
        from_='+12512782757',  
        to=to
    )



class User(db.Model):
    tablename = 'user'
    table_args = {'extend_existing': True}

    id = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(80), nullable=False)
    room = db.Column(db.String(80))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@app.route('/member_ok', methods=['POST'])
def member_ok():
    id = request.form.get('id')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    phone = request.form.get('phone')
    room = request.form.get('room')

    if password != confirm_password:
        error_message = 'Passwords do not match.'
        return render_template('sign.html', error_message=error_message)

    user = User(id=id, phone=phone, room=room)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('login'))



@app.route('/sign', methods=['GET'])
def signup():
    return render_template('sign.html')



@app.route('/sign', methods=['GET', 'POST'])
def sign():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        re_password = request.form.get('re_password')  
        email = request.form.get('email')  # 이메일 가져오기
        hp=request.form.get('hp')  # 휴대폰 번호 가져오기

        if not username or not password or password != re_password:  # 비밀번호 확인
            return redirect(url_for('sign')) 

        user_exists = User.query.filter_by(username=username).first()

        if user_exists:
            return redirect(url_for('sign'))
        
        password_hash = generate_password_hash(password) 
        
        user = User(username=username, password_hash=password_hash, hp=hp, email=email)  # 사용자 생성 시 이메일도 저장 
        
        db.session.add(user)
        db.session.commit()

         # 가입 성공 후 회원가입 페이지로 리다이렉션 
        return redirect(url_for('index'))
   
    return render_template('sign.html')



@app.route('/admin')
def admin():
    if not is_admin():
        # 관리자가 아니면 로그인 페이지로 리디렉션
        return redirect(url_for('login'))
    users = User.query.all()
    for user in users:
        print(user.__dict__)
    return render_template('admin.html', users=users)

def is_admin():
    return session.get('is_admin', False)  # 세션에서 관리자 여부를 가져옴

@app.route('/back_to_index')
def back_to_index():
   return redirect(url_for('index'))


@app.route('/user_info')
def user_info():
    # 세션에서 사용자 이름을 가져옴
    username = session.get('username')

    if not username:
        return redirect(url_for('login')) 

    # 이 사용자 이름과 연결된 사용자 객체에 대한 데이터베이스를 쿼리
    user = User.query.filter_by(username=username).first()

    # 사용자 객체를 render_template 함수에 전달
    return render_template('user_info.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        id = request.form.get('userid')
        password = request.form.get('password')
        
        if not id or not password:
            return redirect(url_for('login')) 

        user = User.query.filter_by(id=id).first()
        
        if user and user.check_password(password):
            # 비밀번호가 일치하면 세션에 사용자 정보 저장
            session['username'] = id
            # 관리자 확인
            if id == 'admin' and password == 'admin':
                session['is_admin'] = True
                return redirect(url_for('admin'))
            else:
                session['is_admin'] = False
                return redirect(url_for('index')) 
        else:
            # 로그인 실패 시, 다시 로그인 페이지로
            return redirect(url_for('login')) 

    else:
        return render_template('login.html')
    

@app.route('/logout')
def logout():
    # 세션에서 사용자 정보 제거

    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        # 여기에 암호 변경 로직 구현
        pass

    return render_template('change_password.html')


@app.route('/user_info')
def another_user_info():
    # 데이터베이스에서 현재 로그인한 사용자만 가져옴

    username = session.get('username')

    if not username:
        return redirect(url_for('login')) 

    # username과 연관된 사용자 개체에 대한 데이터베이스를 쿼리합니다.
    user = User.query.filter_by(username=username).first()

     # User를 render_template 함수에 전달
    return render_template('user_info.html', user=user)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


can_send_notification = True

def send_notification():
    global can_send_notification
    if can_send_notification:
        notification.notify(
            title='긴급 알림',
            message='[Web 발신] 생활중 이상 동작이 감지되어 긴급 알림을 발송해드립니다.',
            timeout=1000  # 알림이 표시되는 시간(초)
        )
        can_send_notification = False  # 알림을 보낸 후에는 플래그를 False로 설정
        threading.Timer(60, reset_flag).start()  # 1분 후에 플래그를 다시 True로 설정하는 타이머 시작

def reset_flag():
    global can_send_notification
    can_send_notification = True  # 플래그를 다시 True로 설정



mp_drawing=mp.solutions.drawing_utils  
mp_pose=mp.solutions.pose

def generate_frames():
    cap = cv2.VideoCapture(0)
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break
            
            image = cv2.resize(image, (640,480))
            #cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2400)
            #cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            # Gaussian blur 추가
            image = cv2.GaussianBlur(image, (5, 5), 0)
            
            
            # RGB로 변환 코드
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        
            # 이미지 처리후 포즈 감지 (Check)
            results = pose.process(image)

            # 다시 BGR로 변환
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS)


                coord_dict={}
                for id_, lm in enumerate(results.pose_landmarks.landmark):
                    h,w,c=image.shape
                    cx,cy=int(lm.x*w), int(lm.y*h)
                    coord_dict[id_] = [cx,cy]

                try:
                    hip_to_neck_dist = abs(coord_dict[23][1] - coord_dict[12][1])  # 엉덩이(23)와 목(12)의 거리
                    head_to_feet_dist = abs(coord_dict[24][1] - coord_dict[11][1])  # 머리(11)와 발(24)의 y 좌표 차이
                    hip_to_knee_dist = abs(coord_dict[23][1] - coord_dict[25][1])  # 엉덩이(23)와 무릎(25)의 y 좌표 차이
                    knee_to_ankle_dist = abs(coord_dict[25][1] - coord_dict[27][1])  # 무릎(25)와 발목(27)의 y 좌표 차이 
                    


                    if hip_to_neck_dist > h/3:
                        if head_to_feet_dist < h/6:  
                            cv2.putText(image,'But maybe just lying down',(50,100),cv2.FONT_HERSHEY_SIMPLEX ,1,(255,0,0), 4,cv2.LINE_AA)
                        else:
                            
                            cv2.putText(image,'Person has fallen',(50,50),cv2.FONT_HERSHEY_SIMPLEX ,1,(255,0,0), 4,cv2.LINE_AA)
    
                            # 가입한 사용자의 전화번호를 가져오기 
                            #user_hp = User.query.filter_by(username=session['username']).first().hp

                            # SMS 전송 
                            #send_sms(user_hp, "경고: 사용자가 쓰러졌습니다. 확인하세요.")
                            send_notification()



                    elif hip_to_knee_dist > h/6 and knee_to_ankle_dist < h/6:  # 앉은 상태 판별 조건 추가
                        cv2.putText(image,'Person is sitting',(50,150),cv2.FONT_HERSHEY_SIMPLEX ,1,(255,0,0), 4,cv2.LINE_AA)
                    else: 
                        cv2.putText(image,'Person is standing',(50,100),cv2.FONT_HERSHEY_SIMPLEX ,1,(255,0,0), 4,cv2.LINE_AA) 
                except Exception as e: 
                    pass

            ret, buffer = cv2.imencode('.jpg', image)
            frame = buffer.tobytes()

            yield (b'--frame\r\n' 
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # 프레임 연결 


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/')
def main():
    return render_template('main/index.html')

@app.route('/ai')
def ai():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('ai/index.html')


@app.route('/about')
def about():
    return render_template('about/index.html')



if __name__=="__main__":
  basedir=os.path.abspath(os.path.dirname(__file__))
  dbfile=os.path.join(basedir,'db.sqlite')
  app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///'+dbfile
  app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN']=True
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

  with app.app_context():
      db.create_all()

  app.run(host='0.0.0.0', port=5000, debug=True)