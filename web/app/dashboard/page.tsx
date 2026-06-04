"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Archive,
  Brain,
  Clock3,
  Flame,
  MessageSquare,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { analyticsApi, userApi } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";
import { UrgencyBanner } from "@/components/usage/UrgencyBanner";
import { ShareYourFuture } from "@/components/share/ShareYourFuture";
import { PaywallModal } from "@/components/paywall/PaywallModal";

type Viewer = {
  id: string;
  name: string;
  email: string;
  plan: string;
};

type ProfileResponse = {
  id: string;
  name: string;
  email: string;
};

const PERIODS = [7, 14, 30] as const;

const EMOTION_COLORS: Record<string, string> = {
  joy: "#1D9E75",
  sadness: "#4E7AD9",
  anger: "#D95C4E",
  fear: "#7A63D9",
  surprise: "#D9A13B",
  disgust: "#61886E",
  neutral: "#7B7B73",
};

const QUICK_ACTIONS = [
  { id: "simulate", label: "Run Simulation", icon: Sparkles, plan: "pro", desc: "Simulate a future scenario" },
  { id: "twin", label: "AI Twin", icon: Brain, plan: "ultra", desc: "Expand your twin's cognition" },
  { id: "predict", label: "Predict", icon: TrendingUp, plan: "pro", desc: "Deep prediction analysis" },
  { id: "memory", label: "Memory", icon: Archive, plan: "free", desc: "Review stored memories" },
] as const;

const PLAN_RANK: Record<string, number> = { free: 0, pro: 1, ultra: 2 };

function formatDateLabel(timestamp: string) {
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(timestamp: string) {
  return new Date(timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function readSavedPlan() {
  if (typeof window === "undefined") {
    return "free";
  }

  try {
    const saved = sessionStorage.getItem("nt_user");
    if (!saved) {
      return "free";
    }

    const parsed = JSON.parse(saved);
    return parsed?.plan || "free";
  } catch {
    return "free";
  }
}

export default function DashboardPage() {
  const router = useRouter();
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [paywallFeature, setPaywallFeature] = useState<{ name: string; action: string; plan: string } | null>(null);
  const [upgradeSuccess, setUpgradeSuccess] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("nt_access_token");
    if (!token) {
      router.replace("/auth/login");
      return;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("upgraded") === "1") {
      setUpgradeSuccess(true);
    }
  }, [router]);

  useEffect(() => {
    let cancelled = false;

    const loadDashboard = async () => {
      const token = localStorage.getItem("nt_access_token");
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const [profile, summary] = await Promise.all([
          userApi.getProfile() as Promise<ProfileResponse>,
          analyticsApi.summary(period) as Promise<AnalyticsSummary>,
        ]);

        if (cancelled) {
          return;
        }

        setViewer({
          id: profile.id,
          name: profile.name || "User",
          email: profile.email,
          plan: readSavedPlan(),
        });
        setAnalytics(summary);
      } catch (err: any) {
        if (cancelled) {
          return;
        }

        if (err?.response?.status === 401) {
          router.replace("/auth/login");
          return;
        }

        setError("Unable to load your dashboard right now.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [period, router]);

  const canAccess = (requiredPlan: string) =>
    (PLAN_RANK[viewer?.plan || "free"] ?? 0) >= (PLAN_RANK[requiredPlan] ?? 0);

  const handleAction = (action: (typeof QUICK_ACTIONS)[number]) => {
    if (!canAccess(action.plan)) {
      setPaywallFeature({ name: action.label, action: action.desc, plan: action.plan });
      return;
    }

    router.push(`/${action.id}`);
  };

  const moodBars = useMemo(() => {
    if (!analytics?.mood_timeline?.length) {
      return [];
    }

    return analytics.mood_timeline.slice(-8).map((point) => ({
      label: formatDateLabel(point.timestamp),
      emotion: point.emotion,
      intensityPercent: Math.max(8, Math.round(point.intensity * 100)),
      color: EMOTION_COLORS[point.emotion] || EMOTION_COLORS.neutral,
    }));
  }, [analytics]);

  const latestMood = analytics?.mood_timeline?.[analytics.mood_timeline.length - 1];
  const firstName = viewer?.name?.split(" ")[0] || "there";
  const engagementPercent = Math.round((analytics?.engagement_score || 0) * 100);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "#F6F4EC" }}>
        <UrgencyBanner />
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "48px 20px 72px" }}>
          <div style={{ display: "grid", gap: 18 }}>
            <div style={{ height: 120, borderRadius: 24, background: "linear-gradient(135deg, #EEE8DA, #F9F6EE)" }} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 14 }}>
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  style={{ height: 112, borderRadius: 18, background: "#FFFFFF", border: "1px solid #E7E0D1" }}
                />
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", gap: 18 }}>
              <div style={{ height: 320, borderRadius: 22, background: "#FFFFFF", border: "1px solid #E7E0D1" }} />
              <div style={{ height: 320, borderRadius: 22, background: "#FFFFFF", border: "1px solid #E7E0D1" }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#F6F4EC" }}>
      <UrgencyBanner />

      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "32px 20px 72px" }}>
        {upgradeSuccess && (
          <div
            style={{
              background: "#EAF3DE",
              border: "1px solid #97C459",
              borderRadius: 14,
              padding: "12px 18px",
              fontSize: 13,
              color: "#3B6D11",
              marginBottom: 18,
            }}
          >
            Plan upgraded successfully. Your new features are now available.
          </div>
        )}

        <section
          style={{
            background: "linear-gradient(135deg, #1A302B 0%, #23463E 52%, #E7D8B5 160%)",
            borderRadius: 28,
            padding: "28px 28px 24px",
            color: "#F8F7F2",
            position: "relative",
            overflow: "hidden",
            marginBottom: 18,
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "auto -80px -90px auto",
              width: 260,
              height: 260,
              borderRadius: "50%",
              background: "radial-gradient(circle, rgba(255,255,255,0.14), transparent 70%)",
            }}
          />

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 18,
              flexWrap: "wrap",
              position: "relative",
            }}
          >
            <div style={{ maxWidth: 640 }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: 999,
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                  marginBottom: 16,
                }}
              >
                <Sparkles size={14} />
                LIVE COGNITION SNAPSHOT
              </div>

              <h1 style={{ fontSize: 34, lineHeight: 1.05, fontWeight: 800, margin: "0 0 12px" }}>
                Welcome back, {firstName}
              </h1>

              <p style={{ fontSize: 15, lineHeight: 1.7, color: "rgba(248,247,242,0.82)", margin: 0 }}>
                Your dashboard is now pulling directly from PostgreSQL. Over the last {period} days, you have
                logged {analytics?.total_sessions || 0} sessions, sent {analytics?.total_messages || 0} messages,
                and your current engagement score is {engagementPercent}%.
              </p>
            </div>

            <div style={{ display: "grid", gap: 10, minWidth: 220 }}>
              <div
                style={{
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 18,
                  padding: "14px 16px",
                }}
              >
                <div style={{ fontSize: 11, letterSpacing: "0.08em", opacity: 0.72, marginBottom: 6 }}>
                  CURRENT PLAN
                </div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{(viewer?.plan || "free").toUpperCase()}</div>
              </div>

              <div
                style={{
                  display: "flex",
                  gap: 8,
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  padding: 6,
                  borderRadius: 999,
                }}
              >
                {PERIODS.map((days) => (
                  <button
                    key={days}
                    onClick={() => setPeriod(days)}
                    style={{
                      flex: 1,
                      border: "none",
                      borderRadius: 999,
                      padding: "10px 12px",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                      background: period === days ? "#F8F7F2" : "transparent",
                      color: period === days ? "#1A302B" : "#F8F7F2",
                    }}
                  >
                    {days}d
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {error && (
          <div
            style={{
              background: "#FCEBEB",
              border: "1px solid #F09595",
              borderRadius: 14,
              padding: "12px 16px",
              color: "#A32D2D",
              fontSize: 13,
              marginBottom: 18,
            }}
          >
            {error}
          </div>
        )}

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
            gap: 14,
            marginBottom: 18,
          }}
        >
          {[
            {
              label: "Sessions",
              value: analytics?.total_sessions || 0,
              detail: `Tracked in the last ${period} days`,
              icon: Activity,
              accent: "#1D9E75",
            },
            {
              label: "Messages",
              value: analytics?.total_messages || 0,
              detail: "Counted from conversation_messages",
              icon: MessageSquare,
              accent: "#4E7AD9",
            },
            {
              label: "Avg Session",
              value: `${(analytics?.avg_session_length_minutes || 0).toFixed(1)} min`,
              detail: "Completed sessions only",
              icon: Clock3,
              accent: "#C27A22",
            },
            {
              label: "Engagement",
              value: `${engagementPercent}%`,
              detail: "Blend of message and session cadence",
              icon: TrendingUp,
              accent: "#7A63D9",
            },
          ].map((card) => (
            <div
              key={card.label}
              style={{
                background: "#FFFFFF",
                border: "1px solid #E7E0D1",
                borderRadius: 20,
                padding: "18px 18px 16px",
                boxShadow: "0 10px 24px rgba(44,44,42,0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#5B5A53" }}>{card.label}</div>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 12,
                    background: `${card.accent}18`,
                    color: card.accent,
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <card.icon size={18} />
                </div>
              </div>

              <div style={{ fontSize: 30, lineHeight: 1, fontWeight: 800, color: "#1A1A18", marginBottom: 8 }}>
                {card.value}
              </div>

              <div style={{ fontSize: 12, color: "#7B7B73" }}>{card.detail}</div>
            </div>
          ))}
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1.6fr) minmax(0,1fr)",
            gap: 18,
            marginBottom: 18,
          }}
          className="dashboard-grid"
        >
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E7E0D1",
              borderRadius: 22,
              padding: "22px 22px 20px",
              boxShadow: "0 10px 24px rgba(44,44,42,0.04)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#1A1A18", marginBottom: 6 }}>
                  Mood timeline
                </div>
                <div style={{ fontSize: 13, color: "#7B7B73", lineHeight: 1.6 }}>
                  Emotion events are read from the database and plotted by recency.
                </div>
              </div>

              {latestMood && (
                <div
                  style={{
                    padding: "10px 12px",
                    borderRadius: 14,
                    background: "#F7F4EC",
                    border: "1px solid #ECE3D2",
                    minWidth: 140,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#7B7B73", marginBottom: 4 }}>Latest mood</div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: EMOTION_COLORS[latestMood.emotion] || "#1A1A18" }}>
                    {latestMood.emotion}
                  </div>
                  <div style={{ fontSize: 12, color: "#7B7B73", marginTop: 2 }}>
                    {Math.round(latestMood.intensity * 100)}% intensity
                  </div>
                </div>
              )}
            </div>

            {moodBars.length > 0 ? (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${moodBars.length}, minmax(0, 1fr))`,
                    gap: 12,
                    alignItems: "end",
                    minHeight: 200,
                    paddingTop: 12,
                  }}
                >
                  {moodBars.map((bar) => (
                    <div key={`${bar.label}-${bar.emotion}`} style={{ display: "grid", gap: 10, justifyItems: "center" }}>
                      <div
                        style={{
                          width: "100%",
                          maxWidth: 56,
                          height: 170,
                          background: "#F3EEE2",
                          borderRadius: 999,
                          display: "flex",
                          alignItems: "flex-end",
                          padding: 6,
                        }}
                      >
                        <div
                          title={`${bar.emotion} ${bar.intensityPercent}%`}
                          style={{
                            width: "100%",
                            height: `${bar.intensityPercent}%`,
                            minHeight: 12,
                            borderRadius: 999,
                            background: `linear-gradient(180deg, ${bar.color}, ${bar.color}CC)`,
                            transition: "height 0.3s ease",
                          }}
                        />
                      </div>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: "#34332F", textTransform: "capitalize" }}>
                          {bar.emotion}
                        </div>
                        <div style={{ fontSize: 11, color: "#8A887F", marginTop: 3 }}>{bar.label}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 16, fontSize: 12, color: "#7B7B73" }}>
                  Showing the latest {moodBars.length} mood points from your selected window.
                </div>
              </>
            ) : (
              <div
                style={{
                  background: "#F7F4EC",
                  border: "1px dashed #D9D0BC",
                  borderRadius: 18,
                  padding: "28px 18px",
                  textAlign: "center",
                  color: "#6D6B63",
                }}
              >
                No mood events have been recorded yet. Start chatting and your emotional timeline will appear here.
              </div>
            )}
          </div>

          <div style={{ display: "grid", gap: 18 }}>
            <div
              style={{
                background: "#FFFFFF",
                border: "1px solid #E7E0D1",
                borderRadius: 22,
                padding: "22px 22px 20px",
                boxShadow: "0 10px 24px rgba(44,44,42,0.04)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 12,
                    background: "#FFF1DE",
                    color: "#C27A22",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <Flame size={17} />
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: "#1A1A18" }}>Top topics</div>
                  <div style={{ fontSize: 12, color: "#7B7B73" }}>Extracted from recent user messages</div>
                </div>
              </div>

              {analytics?.top_topics?.length ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {analytics.top_topics.slice(0, 6).map((topic, index) => (
                    <div
                      key={topic.topic}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "auto 1fr auto",
                        gap: 12,
                        alignItems: "center",
                        padding: "10px 12px",
                        borderRadius: 14,
                        background: index === 0 ? "#F7F4EC" : "#FBFAF6",
                        border: "1px solid #EEE7D8",
                      }}
                    >
                      <div
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 999,
                          background: "#1A302B",
                          color: "#F8F7F2",
                          fontSize: 12,
                          fontWeight: 800,
                          display: "grid",
                          placeItems: "center",
                        }}
                      >
                        {index + 1}
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#1A1A18", textTransform: "capitalize" }}>
                          {topic.topic}
                        </div>
                        <div style={{ fontSize: 11, color: "#7B7B73", marginTop: 3 }}>
                          Last mentioned {formatDateTime(topic.last_mentioned)}
                        </div>
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#4E7AD9" }}>{topic.count}x</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    background: "#F7F4EC",
                    border: "1px dashed #D9D0BC",
                    borderRadius: 18,
                    padding: "24px 16px",
                    color: "#6D6B63",
                    fontSize: 13,
                  }}
                >
                  Topics will start appearing after a few conversations.
                </div>
              )}
            </div>

            <div
              style={{
                background: "#FFFFFF",
                border: "1px solid #E7E0D1",
                borderRadius: 22,
                padding: "22px 22px 20px",
                boxShadow: "0 10px 24px rgba(44,44,42,0.04)",
              }}
            >
              <div style={{ fontSize: 18, fontWeight: 800, color: "#1A1A18", marginBottom: 6 }}>
                Recent emotional pulse
              </div>
              <div style={{ fontSize: 12, color: "#7B7B73", marginBottom: 14 }}>
                A quick read on the latest events captured for your twin.
              </div>

              {analytics?.mood_timeline?.length ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {analytics.mood_timeline.slice(-4).reverse().map((point) => (
                    <div
                      key={`${point.timestamp}-${point.emotion}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        padding: "10px 0",
                        borderBottom: "1px solid #F0EBDD",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span
                          style={{
                            width: 11,
                            height: 11,
                            borderRadius: 999,
                            background: EMOTION_COLORS[point.emotion] || EMOTION_COLORS.neutral,
                            flexShrink: 0,
                          }}
                        />
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: "#1A1A18", textTransform: "capitalize" }}>
                            {point.emotion}
                          </div>
                          <div style={{ fontSize: 11, color: "#7B7B73", marginTop: 2 }}>
                            {formatDateTime(point.timestamp)}
                          </div>
                        </div>
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#5B5A53" }}>
                        {Math.round(point.intensity * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#6D6B63", fontSize: 13 }}>No recent emotional events yet.</div>
              )}
            </div>
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(280px,320px)",
            gap: 18,
          }}
          className="dashboard-secondary-grid"
        >
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E7E0D1",
              borderRadius: 22,
              padding: "22px 22px 20px",
              boxShadow: "0 10px 24px rgba(44,44,42,0.04)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#1A1A18", marginBottom: 6 }}>
                  Quick actions
                </div>
                <div style={{ fontSize: 12, color: "#7B7B73", lineHeight: 1.6 }}>
                  Keep moving without leaving your dashboard.
                </div>
              </div>

              <a
                href="/pricing"
                style={{
                  background: "#1A1A18",
                  color: "#FFFFFF",
                  borderRadius: 10,
                  padding: "10px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                }}
              >
                Upgrade plan
              </a>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 12 }}>
              {QUICK_ACTIONS.map((action) => {
                const locked = !canAccess(action.plan);
                const Icon = action.icon;

                return (
                  <button
                    key={action.id}
                    onClick={() => handleAction(action)}
                    style={{
                      background: locked ? "#FCFBF8" : "#F8F7F2",
                      border: `1.5px solid ${locked ? "#E5E2D9" : "#D7D2C4"}`,
                      borderRadius: 16,
                      padding: "18px 16px",
                      textAlign: "left",
                      cursor: "pointer",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        width: 42,
                        height: 42,
                        borderRadius: 14,
                        background: locked ? "#F3EEE4" : "#E6F1FB",
                        color: locked ? "#7B7B73" : "#185FA5",
                        display: "grid",
                        placeItems: "center",
                        marginBottom: 12,
                      }}
                    >
                      <Icon size={19} />
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "#1A1A18", marginBottom: 4 }}>{action.label}</div>
                    <div style={{ fontSize: 12, color: "#7B7B73", lineHeight: 1.5 }}>{action.desc}</div>
                    {locked && (
                      <span
                        style={{
                          position: "absolute",
                          top: 12,
                          right: 12,
                          fontSize: 10,
                          background: "#FAEEDA",
                          color: "#854F0B",
                          border: "1px solid #EF9F27",
                          borderRadius: 999,
                          padding: "2px 8px",
                          fontWeight: 800,
                        }}
                      >
                        {action.plan.toUpperCase()}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            {viewer && <ShareYourFuture userId={viewer.id} />}
          </div>
        </section>
      </div>

      {paywallFeature && (
        <PaywallModal
          isOpen={true}
          onClose={() => setPaywallFeature(null)}
          featureName={paywallFeature.name}
          blockedAction={paywallFeature.action}
          plan={paywallFeature.plan}
        />
      )}

      <style jsx>{`
        @media (max-width: 920px) {
          :global(.dashboard-grid) {
            grid-template-columns: 1fr !important;
          }

          :global(.dashboard-secondary-grid) {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
