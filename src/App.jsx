import { useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import PixelTransition from "./components/PixelTransition";

gsap.registerPlugin(ScrollTrigger);

const imageUrl = (name) => `/images/${name}`;

const slides = [
  {
    title: "COASTAL ROUTE",
    badge: "海岸线推荐",
    copy: "为海边、公路、日落和轻户外场景准备的旅行灵感，适合快速浏览并进入高完成度路线。",
    highlight: "海岸风景 / 日落 / 慢旅行",
    image: imageUrl("pexels-jyjyjyjy-21071576.jpg"),
    statA: "12",
    statB: "热门海边目的地",
    statC: "24H",
    statD: "随时切换主题",
  },
  {
    title: "CITY FRAME",
    badge: "城市轻攻略",
    copy: "围绕城市街区、咖啡馆、夜景和拍照点展开，用更克制的结构把内容做成可浏览的推荐体验。",
    highlight: "街区漫游 / 咖啡馆 / 夜拍",
    image: imageUrl("pexels-k-zhao-44056406-34809836.jpg"),
    statA: "08",
    statB: "精选城市主题",
    statC: "03",
    statD: "页面模块",
  },
  {
    title: "LOCAL FLAVOR",
    badge: "在地体验",
    copy: "把餐饮、路线、风景与本地玩法放在同一套视觉秩序里，方便用户快速完成出行决策。",
    highlight: "美食 / 玩法 / 小众点位",
    image: imageUrl("pexels-fotoslian-2875254.jpg"),
    statA: "05",
    statB: "生活方式专题",
    statC: "1:1",
    statD: "高密度信息",
  },
  {
    title: "WIDE JOURNEY",
    badge: "长线路线",
    copy: "适合周末到长假的旅行规划，强调连贯的路线流动、主题分类和更有视觉层次的推荐内容。",
    highlight: "长线 / 风景公路 / 主题规划",
    image: imageUrl("pexels-open-borders-36907667.jpg"),
    statA: "16",
    statB: "路线模板",
    statC: "60",
    statD: "推荐场景",
  },
];

const featureCards = [
  { index: "01", title: "目的地筛选", text: "按季节、氛围和出行动机聚合内容，让用户快速进入适合自己的旅行场景。" },
  { index: "02", title: "路线推荐", text: "把城市、自然、海岸和在地体验拆成清晰模块，便于浏览、收藏和继续延伸。" },
  { index: "03", title: "视觉叙事", text: "用大图、毛玻璃和慢节奏动效拉高质感，让页面像设计师作品集一样干净有力。" },
];

const editorialCards = [
  { title: "精选路线", text: "把不同类型的旅行路径做成一组可切换的视觉章节。" },
  { title: "灵感收藏", text: "高对比封面和轻量文案，让内容既像杂志也像工具。" },
  { title: "深度浏览", text: "滚动进入时的大标题、卡片和图像依次出现，形成清晰节奏。" },
  { title: "页面秩序", text: "控制版心、间距和动效强度，把信息密度收束到 1700px 宽的主视觉中。" },
];

function App() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const rootRef = useRef(null);
  const introRef = useRef(null);
  const heroCopyRef = useRef(null);
  const heroTitleRef = useRef(null);
  const heroMetaRef = useRef(null);
  const heroActionsRef = useRef(null);
  const heroStageRef = useRef(null);

  const current = slides[currentSlide];
  const next = slides[(currentSlide + 1) % slides.length];

  useEffect(() => {
    const ctx = gsap.context(() => {
      const intro = introRef.current;
      const copy = heroCopyRef.current;
      const title = heroTitleRef.current;
      const meta = heroMetaRef.current;
      const actions = heroActionsRef.current;
      const stage = heroStageRef.current;
      if (!intro || !copy || !title || !meta || !actions || !stage) return;

      const tl = gsap.timeline({ defaults: { ease: "power4.out" } });
      tl.set([copy, meta, actions, stage], { autoAlpha: 0 });
      tl.set(title.querySelectorAll("[data-line]"), {
        yPercent: 120,
        scaleY: 1.14,
        transformOrigin: "top left",
      });

      tl.to(intro, { xPercent: 100, duration: 1.15 }, 0.12)
        .to(copy, { autoAlpha: 1, duration: 0.12 }, 0.26)
        .to(stage, { autoAlpha: 1, x: 0, scale: 1, duration: 1 }, 0.25)
        .to(
          title.querySelectorAll("[data-line]"),
          {
            yPercent: 0,
            scaleY: 1,
            duration: 0.95,
            stagger: 0.08,
          },
          0.4
        )
        .to(meta, { autoAlpha: 1, y: 0, duration: 0.72 }, 0.72)
        .to(actions, { autoAlpha: 1, y: 0, duration: 0.72 }, 0.82);
    }, rootRef);

    return () => ctx.revert();
  }, []);

  useEffect(() => {
    const copy = heroCopyRef.current;
    if (!copy) return undefined;

    const reveal = copy.querySelectorAll("[data-reveal]");
    if (transitioning) {
      gsap.to(reveal, {
        y: 24,
        autoAlpha: 0,
        duration: 0.3,
        stagger: 0.03,
        ease: "power2.in",
      });
      return undefined;
    }

    gsap.fromTo(
      reveal,
      { y: 28, autoAlpha: 0, scaleY: 1.08, transformOrigin: "top left" },
      {
        y: 0,
        autoAlpha: 1,
        scaleY: 1,
        duration: 0.9,
        stagger: 0.06,
        ease: "power4.out",
      }
    );

    return undefined;
  }, [currentSlide, transitioning]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setTransitioning((state) => (state ? state : true));
    }, 6200);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const sections = gsap.utils.toArray(".reveal-section");

      sections.forEach((section) => {
        const title = section.querySelector("[data-section-title]");
        const intro = section.querySelector("[data-section-intro]");
        const cards = section.querySelectorAll("[data-section-card]");
        const visual = section.querySelector("[data-section-visual]");
        const figure = section.querySelector("[data-section-figure]");

        if (title) gsap.set(title, { autoAlpha: 0, y: 120, scaleY: 1.16, transformOrigin: "top left" });
        if (intro) gsap.set(intro, { autoAlpha: 0, y: 28 });
        if (cards.length) gsap.set(cards, { autoAlpha: 0, y: 42 });
        if (visual) gsap.set(visual, { autoAlpha: 0, x: 24, scale: 0.98 });
        if (figure) gsap.set(figure, { yPercent: 10 });

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: "top 72%",
            end: "bottom 30%",
            toggleActions: "play none none reverse",
          },
          defaults: { ease: "power4.out" },
        });

        tl.to(title, { autoAlpha: 1, y: 0, scaleY: 1, duration: 0.95 })
          .to(intro, { autoAlpha: 1, y: 0, duration: 0.56 }, 0.18)
          .to(cards, { autoAlpha: 1, y: 0, duration: 0.7, stagger: 0.1 }, 0.24)
          .to(visual, { autoAlpha: 1, x: 0, scale: 1, duration: 0.8 }, 0.32);

        if (figure) {
          gsap.to(figure, {
            yPercent: -6,
            ease: "none",
            scrollTrigger: {
              trigger: section,
              start: "top bottom",
              end: "bottom top",
              scrub: 1,
            },
          });
        }
      });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  const heroStats = useMemo(
    () => [
      { value: current.statA, label: current.statB },
      { value: current.statC, label: current.statD },
    ],
    [current]
  );

  return (
    <div className="app-shell" ref={rootRef}>
      <div className="site-grain" aria-hidden="true" />
      <div className="site-vignette" aria-hidden="true" />
      <div className="intro-curtain" ref={introRef} aria-hidden="true" />

      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <div>
            <strong>TRAVEL STUDIO</strong>
            <p>旅游推荐</p>
          </div>
        </div>
        <div className="topbar-meta">
          <span>城市</span>
          <span>风格</span>
          <span>风景</span>
        </div>
      </header>

      <main className="page">
        <section className="hero reveal-section">
          <div className="container hero-grid">
            <div className="hero-copy" ref={heroCopyRef}>
              <span className="hero-kicker" data-reveal>
                TRAVEL RECOMMENDATION WEBSITE
              </span>
              <h1 className="hero-title" ref={heroTitleRef}>
                <span className="hero-line" data-line>
                  <span data-reveal>TRAVEL</span>
                </span>
                <span className="hero-line hero-line--accent" data-line>
                  <span data-reveal>RECOMMENDER</span>
                </span>
              </h1>
              <p className="hero-lead" data-reveal>
                以高端作品集式的视觉语言重构旅行推荐网站：大标题、毛玻璃、慢节奏动效和图片轮换
                共同组成一个适合 PC 端展示的介绍页面。
              </p>
              <div className="hero-actions" ref={heroActionsRef} data-reveal>
                <button type="button" className="hero-button hero-button--solid">
                  Explore routes
                </button>
                <button type="button" className="hero-button hero-button--ghost" onClick={() => setTransitioning(true)}>
                  Next story
                </button>
              </div>

              <div className="hero-meta" ref={heroMetaRef}>
                <div className="meta-card">
                  <span>当前主题</span>
                  <strong>{current.badge}</strong>
                </div>
                <div className="meta-card">
                  <span>内容方向</span>
                  <strong>{current.highlight}</strong>
                </div>
              </div>
            </div>

            <div className="hero-stage" ref={heroStageRef}>
              <PixelTransition
                active={transitioning}
                firstContent={<img src={current.image} alt={current.title} className="stage-image" loading="eager" />}
                secondContent={<img src={next.image} alt={next.title} className="stage-image" loading="eager" />}
                gridSize={11}
                pixelColor="rgba(12, 16, 14, 0.96)"
                animationStepDuration={0.82}
                aspectRatio="16 / 10"
                onComplete={() => {
                  setCurrentSlide((value) => (value + 1) % slides.length);
                  setTransitioning(false);
                }}
                className="stage-transition"
              />
            </div>

            <div className="hero-caption">
              <span>{current.badge}</span>
              <strong>{current.title}</strong>
              <p>{current.copy}</p>
              <div className="hero-stat-strip hero-stat-strip--below">
                {heroStats.map((item) => (
                  <div key={item.label} className="stat-chip">
                    <strong>{item.value}</strong>
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="module reveal-section">
          <div className="container module-grid module-grid--features">
            <div className="module-heading">
              <span className="module-index">01</span>
              <h2 data-section-title>WHAT THE SITE SHOWS</h2>
              <p data-section-intro>
                介绍页本身保持克制，主要用来说明网站如何提供目的地推荐、路线筛选、内容收藏和主题浏览。
              </p>
            </div>

            <div className="module-cards">
              {featureCards.map((card) => (
                <article key={card.index} className="glass-card" data-section-card>
                  <span>{card.index}</span>
                  <strong>{card.title}</strong>
                  <p>{card.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="module reveal-section">
          <div className="container module-grid module-grid--split">
            <div className="module-copy">
              <span className="module-index">02</span>
              <h2 data-section-title>EDITORIAL ROUTES</h2>
              <p data-section-intro>
                页面把旅行内容整理成分层结构，先看大标题，再看卡片，最后通过图片和轻微视差收住节奏。
              </p>

              <div className="editorial-list">
                {editorialCards.map((card, index) => (
                  <article key={card.title} className="editorial-item" data-section-card>
                    <span>0{index + 1}</span>
                    <div>
                      <strong>{card.title}</strong>
                      <p>{card.text}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="module-visual" data-section-visual>
              <div className="figure-frame" data-section-figure>
                <img src={imageUrl("pexels-jerry-wang-2135752-11633454.jpg")} alt="Travel landscape" />
                <div className="figure-glass">
                  <span>Visual rhythm</span>
                  <strong>Slow reveal and calm hierarchy</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="module reveal-section module--closing">
          <div className="container module-grid module-grid--closing">
            <div className="closing-copy">
              <span className="module-index">03</span>
              <h2 data-section-title>DESIGNED TO FEEL PREMIUM</h2>
              <p data-section-intro>
                这是一版基础可运行原型，核心是把素材、节奏和版心先稳住，后面可以继续往 UI 细节和交互深度上迭代。
              </p>
            </div>

            <div className="closing-card-row">
              <div className="closing-card" data-section-card>
                <strong>ScrollTrigger</strong>
                <span>标题先入，卡片后入，图片再做轻微位移动画。</span>
              </div>
              <div className="closing-card" data-section-card>
                <strong>Pixel rotation</strong>
                <span>首屏背景轮换用像素过渡，避免普通淡入带来的廉价感。</span>
              </div>
              <div className="closing-card" data-section-card>
                <strong>1700px frame</strong>
                <span>整体版心收束，适合 PC 端展示和后续继续精修。</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
