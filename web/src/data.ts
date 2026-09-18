export const worlds = [
  {
    name: "눈 덮인 해안",
    en: "SNOW COAST",
    image: "scene-snow-coast.png",
    tag: "모든 모험의 시작",
    description:
      "햇빛이 반짝이는 첫 해안. 눈 위를 걷고 발판을 건너며 물고기를 찾으세요. 얼음 구멍 아래에는 또 다른 세계가 기다립니다.",
    terrain: "눈밭 · 잠수 구멍",
    enemy: "게 · 돌진하는 물범",
    mission: "첫 물고기를 모으고 해양 탐험에 도전하기",
    color: "#c5dfec",
  },
  {
    name: "미끄러운 빙하",
    en: "GLACIER CANYON",
    image: "scene-glacier-canyon.png",
    tag: "조금 더 멀리, 미끄러져요",
    description:
      "푸른 얼음 위에서는 움직임의 관성이 남습니다. 높은 발판으로 올라가 얼음 껍질에 갇힌 아기 펭귄을 찾아보세요.",
    terrain: "미끄러운 얼음 · 높은 발판",
    enemy: "뛰어오르는 얼음 정령",
    mission: "활주로 얼음 껍질을 깨고 친구 구조하기",
    color: "#bde6e9",
  },
  {
    name: "얼음 동굴",
    en: "ICE CAVERN",
    image: "scene-ice-cave.png",
    tag: "어둠 속 작은 빛을 따라서",
    description:
      "얼음 동굴 입구에서 안쪽으로 들어가 보세요. 낮은 통로를 미끄러져 지나고 세 개의 봉인석을 모으면 보물방의 문을 열 수 있습니다.",
    terrain: "낮은 활주 통로 · 봉인된 보물방",
    enemy: "순찰하는 게 · 얼음 정령",
    mission: "봉인석 3개 → 레버 → 보물 → 지름길 개방",
    color: "#d0d8ea",
  },
  {
    name: "눈보라 고원",
    en: "BLIZZARD RIDGE",
    image: "scene-blizzard-plateau.png",
    tag: "바람도 모험의 일부",
    description:
      "눈보라는 왼쪽으로 등을 밀어냅니다. 서두르지 말고 길을 살피세요. 배고픈 친구에게 물고기 세 마리를 나눠주면 함께 걸을 수 있습니다.",
    terrain: "강한 바람 · 눈보라",
    enemy: "낮게 날아드는 도둑갈매기",
    mission: "먹이 3개를 나누고 친구를 이글루로 데려가기",
    color: "#dbe1e3",
  },
  {
    name: "갈라진 빙붕",
    en: "FRACTURED SHELF",
    image: "scene-fractured-shelf.png",
    tag: "멈추지 않는 작은 발걸음",
    description:
      "발판이 흔들리면 무너지기 전에 다음 발판으로 이동하세요. 제한시간 안에 빙붕을 건너거나, 무너진 동굴의 옆길을 탐험할 수 있습니다.",
    terrain: "무너지는 다리 · 선택 동굴",
    enemy: "물범 · 얼음 정령",
    mission: "32초 안에 빙붕 탈출하기",
    color: "#d6ddeb",
  },
  {
    name: "펭귄의 보금자리",
    en: "SUNSET HOME",
    image: "scene-sunset-home.png",
    tag: "함께 돌아오는 곳",
    description:
      "친구들과 돌아와 따뜻한 둥지와 깃발, 꽃밭을 만드세요. 물고기 30마리, 친구 3마리, 빙붕 탈출 기록을 갖추면 모험이 완성됩니다.",
    terrain: "안전지대 · 꾸밀 수 있는 이글루",
    enemy: "이글루 주변은 안전해요",
    mission: "마지막 친구를 구조하고 모두 함께 귀환하기",
    color: "#f0dfca",
  },
];
export const collection = [
  {
    name: "주황 물고기",
    category: "물고기",
    image: "orange-fish.png",
    value: "+10 POINTS",
    description:
      "처음 만나는 든든한 먹이. 점수와 집 꾸미기에 쓸 먹이를 함께 얻어요.",
  },
  {
    name: "파랑 물고기",
    category: "물고기",
    image: "blue-fish.png",
    value: "+25 POINTS",
    description:
      "푸른 바다와 빙하에 숨어 있어요. 높은 옆길도 자세히 살펴보세요.",
  },
  {
    name: "황금 물고기",
    category: "물고기",
    image: "gold-fish.png",
    value: "+50 POINTS",
    description:
      "깊은 바다와 탐험 길 끝의 반짝이는 보상. 돌아갈 길도 잊지 마세요.",
  },
  {
    name: "거대 물약",
    category: "아이템",
    image: "growth-potion.png",
    value: "8초 · 종료 후 보호 1.5초",
    description:
      "몸집이 커져 적을 돌파할 수 있어요. 작은 통로에도 갇히지 않도록 이동 판정은 유지됩니다.",
  },
  {
    name: "가속 물약",
    category: "아이템",
    image: "speed-potion.png",
    value: "8초 · 이동 속도 1.6배",
    description:
      "더 빠른 발걸음으로 넓은 눈밭을 건너요. 발판 끝에서는 속도를 조절하세요.",
  },
  {
    name: "반전 물약",
    category: "아이템",
    image: "reverse-potion.png",
    value: "8초 · 좌우 조작 반전",
    description:
      "왼쪽과 오른쪽이 바뀌어요. 옆길에 한 개만 놓여 있으니 조심해서 선택하세요.",
  },
  {
    name: "아기 펭귄",
    category: "친구와 적",
    image: "baby.png",
    value: "구조 완료 +100 POINTS",
    description:
      "얼음 껍질 깨기, 먹이 나누기, 레버 작동으로 친구의 부탁을 해결한 뒤 이글루까지 동행해요.",
  },
  {
    name: "눈밭의 게",
    category: "친구와 적",
    image: "crab.png",
    value: "처치 +30 POINTS",
    description:
      "짧은 다리로 발판을 순찰해요. 옆으로 닿지 않도록 위에서 밟아주세요.",
  },
  {
    name: "물범",
    category: "친구와 적",
    image: "seal.png",
    value: "처치 +40 POINTS",
    description:
      "가까이 다가가면 잠시 경고한 뒤 빠르게 돌진해요. 경고 표시를 살펴보세요.",
  },
  {
    name: "도둑갈매기",
    category: "친구와 적",
    image: "skua.png",
    value: "처치 +45 POINTS",
    description:
      "날개를 펴고 낮게 날아다녀요. 눈보라 속에서는 더 주의가 필요합니다.",
  },
  {
    name: "얼음 정령",
    category: "친구와 적",
    image: "spirit.png",
    value: "처치 +50 POINTS",
    description:
      "일정한 간격으로 뛰어올라요. 내려오는 순간을 기다리면 안전하게 지나갈 수 있어요.",
  },
  {
    name: "봉인된 보물",
    category: "아이템",
    image: "golden-treasure-chest.png",
    value: "+100 POINTS",
    description:
      "동굴의 봉인석 세 개를 모아 레버로 문을 연 뒤 E로 상자를 열어보세요.",
  },
];
