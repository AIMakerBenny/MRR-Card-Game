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

Phase 23 - 3D 전장 카드 호버·선택 강조
- 마우스가 가리키는 전장 카드만 상승하고 카드 주변에 입체 광륜을 표시합니다.
- 선택한 카드와 공격 대상은 별도 강조됩니다.
- 다른 카드의 위치와 게임 판정은 변경하지 않습니다.
- 원본 2D 호버, 대상 선택, 저장, AI는 Phase21 코드가 담당합니다.
- 빌드: python build.py
- 실행본: Marorong_Card_War_Phase23_3D_Prototype.html
- 실제 WebGL 호버와 게임 상태 불변 여부는 GitHub Actions의 tests/webgl_e2e.py를 통과해야 완료로 보고합니다.

Phase 24 - Three.js 카드 문양과 프레임 개편
- 기존 게임 데이터·능력을 변경하지 않고 유형별 장식 문양과 금속 프레임을 생성합니다.
- 전장 카드 앞면 CanvasTexture, 선택 강조와 금속색이 실제 카드 종류에 맞게 갱신됩니다.
- 카드 이름·체력 및 실제 명령은 기존 HTML에서 계속 표시합니다.
- 실제 Chromium WebGL 카드 텍스처 수 검증을 통과한 뒤 완료 처리합니다.
