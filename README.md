# 남극 펭귄의 물고기 모험

Pygame으로 만든 2D 플랫폼 게임입니다. 남극을 탐험하며 물고기 18마리를 모으세요.

## 실행

Python이 설치된 환경에서 프로젝트 폴더를 열고 실행합니다.

```powershell
python -m pip install -r requirements.txt
python pygame/main.py
```

## 조작

- Enter / 스페이스바: 설명 화면에서 시작
- 방향키 / A, D: 이동
- 스페이스바 / ↑ / W: 점프
- R: 설명 화면부터 재시작
- Esc: 종료

## 게임 규칙

- 주황 물고기 10점, 파랑 물고기 25점, 황금 물고기 50점
- 초록 아이템: 크기 1.5배, 노랑: 속도 1.6배, 보라: 좌우 반전 (각 8초)
- 게를 밟으면 30점. 옆에서 닿거나 추락하면 시작 위치로 복귀합니다.
- 복귀해도 점수는 유지되고 아이템 효과는 해제됩니다.
- 물고기를 모두 모으면 성공합니다. 적 처치는 선택입니다.

## 파일

- `pygame/main.py`: 게임 코드
- `pygame/data/`: 게임 이미지 및 제작 기록
- `requirements.txt`: 실행에 필요한 패키지

게임 이미지는 저장소에 함께 포함해야 합니다. 빌드 도구와 생성된 실행 파일은 `.gitignore`에서 제외합니다. Windows 실행 파일은 GitHub Releases에 별도로 배포할 수 있습니다.


## Adventure expansion

Double-click `pygame/AntarcticPenguin.exe` on Windows; Python is not required.

- 7,200-pixel world with six regions: snowy coast, slippery glacier, ice caves, blizzard plateau, fractured ice shelf and penguin home.
- Collect all 30 fish and rescue three baby penguins to complete the adventure. Touch a baby to carry it, then return to any igloo for a 100-point rescue bonus.
- Igloos are checkpoints for the current game session. Falling or taking damage returns you to your last igloo; carried babies return to their original positions.
- Ice retains momentum, blizzards push left, and cracked platforms collapse after 0.8 seconds and recover after four seconds.
- Explore two cave entrances to reveal treasure chests worth 100 points each. Treasure and enemy defeats are optional.
- R resets all progress and returns to the instructions.
