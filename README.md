# 출근 상태 오버레이
![image](https://github.com/user-attachments/assets/5e42b840-143d-4f01-8d44-e5f66af0d2c3)

## 프로그램 소개
- 현재 출근 상태 및 잔여 복무시간을 모니터에 표기해주는 프로그램으로 3개로 나누어져서 구성됨
- `Auto Refresh Plus | Page Monitor`
  -  Chrome 웹 스토어에서 설치 가능
  -  홈페이지를 주기적으로 새로고침하면서 로그아웃을 방지함
- `Auto Save Page Content`
  -  홈페이지가 새로고침 될 때마다 페이지의 내용을 `page_content_*.json`으로 다운로드함
- `status_overlay.exe`
  -  다운로드 폴더에 있는 `page_content_*.json`을 읽고 정보를 화면에 띄움

## 개발 환경
- Window 11
- Python 3.10.16

## 설치 방법
1. `my_status_overlay_release.zip`의 압축을 풀어서 `Download` 폴더에 넣음
2. `font` 폴더에 있는 폰트들 모두 설치
3. `Chrome` > `Chrome 웹 스토어` > `Auto Refresh Plus | Page Monitor` 설치
4. `Auto Refresh Plus | Page Monitor`의 `설정` > `설정 백업` > `가져오기` > `storage_data.arp`
5. `Chrome` > `확장 프로그램` > `확장 프로그램 관리` > `개발자 모드` ON > `압축해제된 확장 프로그램을 로드합니다` > `auto_save_extension` 선택
6. KRP 홈페이지 로그인
7. `Auto Refresh Plus | Page Monitor`시간 간격 설정 (ex. 900초) 후에 시작 버튼 누르기
9. `my_status_overlay_release` 폴더에 있는 `status_overlay.exe` 실행

## 기능
- `출근` / `퇴근` / `대기` : 상태 표기
- `잔여 00:00` : 금주 잔여 복무시간 표기
- `퇴근 00:00` : 금일의 실제 퇴근 시각 혹은 금일에 40시간을 채울 수 있는 예상 퇴근 시각 표기
- 프로그램 선택 : 붉은 글씨만 가능, 흰 글씨는 선택 안됨
  - 마우스 드래그로 위치 이동
  - 크기 조절 : `+` `-`
  - 투명도 조절 : &#8593; &#8595;
- 작업표시줄의 트레이 기능
  - 상세정보 숨기기 (흰색 글씨)
  - 잠금 / 잠금해제 (붉은 글씨를 눌러도 선택 안됨)
  - 종료
- `config.json`를 지우면 `status_overlay.exe`의 위치, 크기, 투명도 설정이 초기화됨
- 컴퓨터가 절전모드된 동안 다운로드된 `page_content_*.json`들이 쌓이는데, 절전모드가 풀리면 1분 뒤에 바로 지워짐

## 문제 발생 시
- 프로그램에서 상태 표기가 잘못된 것으로 인해 일어나는 일에 대해 책임을 지지 않음
- 수정 요청 시, 당시의 `page_content_*.json`을 첨부해주면 원인을 찾는데 도움이 됨
- 심각한 에러가 아니면 굳이 고칠지는 나도 모름
