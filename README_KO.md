MARORONG CARD WAR - Phase 22 3D Prototype 01

기준: 사용자가 제공한 Phase 21 UI Fixed HTML을 유지한 Three.js 선택형 그래픽 시제품.

원본: legacy/Phase21_Original.html
실행 HTML: Marorong_Card_War_Phase22_3D_Prototype.html
그래픽 코드: src/scene.js, src/boot.js, src/depth.css
빌드 명령: python build.py
3D 라이브러리 로컬 준비: npm install && npm run vendor
검증 명령: python tests/static_audit.py 및 Python Playwright Chromium 검사

게임 데이터와 규칙을 3D 엔진에서 다시 계산하지 않습니다. 3D 레이어는 기존 DOM 및 공개 상태를 읽어서 표현합니다.

미검증 사항: 실물 WebGL Three.js 구동 여부, 모바일 실기기, 개별 카드 일러스트, 모든 능력 간 상호작용. CI 결과를 확인한 후에만 통과로 보고합니다.

이 프로젝트는 별도 빌드를 위한 소스 구조를 제공하며 완성된 3D 게임을 의미하지 않습니다.
