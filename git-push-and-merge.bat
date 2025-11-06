@echo off
chcp 65001 >nul
echo ========================================
echo Git 푸시 및 머지 스크립트
echo ========================================
echo.

echo [1] 현재 Git 상태 확인
git status
echo.
pause

echo [2] 변경사항 스테이징
git add .
echo.

echo [3] 커밋 메시지 입력
set /p COMMIT_MSG="커밋 메시지를 입력하세요 (기본: Update to version 1.5): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update to version 1.5
git commit -m "%COMMIT_MSG%"
echo.

echo [4] secure_coding 브랜치 확인 및 전환
git checkout secure_coding 2>nul
if errorlevel 1 (
    echo secure_coding 브랜치가 없습니다. 생성합니다...
    git checkout -b secure_coding
) else (
    echo secure_coding 브랜치로 전환했습니다.
)
echo.

echo [5] secure_coding 브랜치에 푸시
git push origin secure_coding
echo.

echo [6] main 브랜치로 전환
git checkout main
echo.

echo [7] main 브랜치 최신화 (다른 팀원의 변경사항 가져오기)
git pull origin main
echo.

echo [8] secure_coding 브랜치를 main에 머지
git merge secure_coding
echo.

echo [9] 머지된 내용을 main 브랜치에 푸시
git push origin main
echo.

echo ========================================
echo 모든 작업이 완료되었습니다!
echo ========================================
echo.
echo 현재 브랜치: 
git branch --show-current
echo.
pause

