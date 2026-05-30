# Notion Gallery

이미지와 프롬프트를 노션 스타일로 정리하고 관리할 수 있는 개인 갤러리 프로그램입니다.

## 기능

* 카테고리 생성 및 관리
* 이미지 첨부
* 태그 기능
* 프롬프트 저장
* 내용 검색
* 갤러리 / 리스트 보기
* 다크 모드 지원

---

## 필요 환경

* Python 3.10 이상 권장

---

## macOS 사용법

1. 저장소 ZIP 다운로드
2. 압축 해제
3. `실행하기.command` 실행

만약 실행이 차단되면:

1. 터미널 실행
2. 프로그램 폴더로 이동
3. 아래 명령 실행

```bash
chmod +x 실행하기.command
./실행하기.command
```

---

## CMD 수동 실행

실행하기.command 실패하면?

* 응용 프로그램 → 유틸리티 → 터미널 → 터미널 실행

필요한 라이브러리 설치:

```bash
pip3 install customtkinter pillow
```

프로그램 실행:

```bash
python3 notion_gallery.py
```

---

## 주의사항

프로그램은 현재 폴더에 다음 파일을 생성합니다.

* gallery_data.json
* gallery_images/

프롬프트와 이미지 데이터는 모두 로컬에 저장되며 외부 서버로 전송되지 않습니다.

---

## 사용 라이브러리

* CustomTkinter
* Pillow
* Tkinter
