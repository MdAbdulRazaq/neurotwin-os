"""
NEUROTWIN OS — Visual Identity Engine (Step 1)
Deterministic styling engine that maps emotions to avatar appearance parameters.
No ML/Stable Diffusion — pure rules-based visual state transformation.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.responses import JSONResponse
from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware

# Setup structured logging with trace context
setup_logging(service_name="neurotwin.visual-identity")

logger = logging.getLogger("neurotwin.visual-identity")


# ── Schemas ────────────────────────────────────────────────────────────────────

class EmotionInput(BaseModel):
    """Input emotion data from perception or conversation service."""
    emotion: str = Field(..., description="Detected emotion label (joy, sadness, anger, surprise, fear, disgust, neutral)")
    intensity: float = Field(0.5, ge=0.0, le=1.0, description="Emotion intensity 0.0-1.0")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Detection confidence")
    text_context: Optional[str] = Field(None, description="Optional text context for additional styling cues")

    @field_validator("emotion")
    @classmethod
    def normalize_emotion(cls, v: str) -> str:
        return v.lower().strip()


class ColorPalette(BaseModel):
    """Color palette for avatar styling."""
    primary: str = Field(..., description="Primary accent color (hex)")
    secondary: str = Field(..., description="Secondary accent color (hex)")
    highlight: str = Field(..., description="Highlight color (hex)")
    shadow: str = Field(..., description="Shadow color (hex)")


class EyeFeatures(BaseModel):
    """Eye-related visual parameters."""
    brightness: float = Field(1.0, ge=0.3, le=1.5, description="Eye brightness multiplier")
    size_multiplier: float = Field(1.0, ge=0.5, le=2.0, description="Eye size relative to base")
    sharpness: float = Field(1.0, ge=0.5, le=2.0, description="Edge sharpness")
    pupil_dilation: float = Field(1.0, ge=0.5, le=1.5, description="Pupil size")
    highlight_intensity: float = Field(1.0, ge=0.0, le=2.0, description="Eye highlight strength")


class MouthFeatures(BaseModel):
    """Mouth-related visual parameters."""
    curvature: float = Field(0.0, ge=-1.0, le=1.0, description="Smile curve (-1=frown, 1=big smile)")
    openness: float = Field(0.0, ge=0.0, le=1.0, description="Mouth open amount")
    width: float = Field(1.0, ge=0.5, le=2.0, description="Mouth width relative to base")
    tension: float = Field(0.0, ge=0.0, le=1.0, description="Lip tension (for anger/tense)")


class SkinTone(BaseModel):
    """Skin tone and texture parameters."""
    base_hue: str = Field("#E8BEAC", description="Base skin color (hex)")
    saturation: float = Field(1.0, ge=0.5, le=2.0, description="Color saturation")
    warmth: float = Field(1.0, ge=0.3, le=1.7, description="Warmth filter strength")


class VisualState(BaseModel):
    """Complete visual identity state for an avatar."""
    emotion: str
    intensity: float
    color_palette: ColorPalette
    eye_features: EyeFeatures
    mouth_features: MouthFeatures
    skin_tone: SkinTone
    special_effects: List[str] = Field(default_factory=list)
    metadata: Dict[str, float] = Field(default_factory=dict)


class AvatarStyleResponse(BaseModel):
    """Response with enhanced avatar styling parameters."""
    visual_state: VisualState
    expression_override: Optional[str] = None
    blend_time_ms: int = 300
    description: str = ""


# ── Deterministic Visual Identity Rules ───────────────────────────────────────

class VisualIdentityEngine:
    """
    Deterministic rules-based engine that maps emotions to visual appearance.
    No ML or generative models — pure mathematical transformations.
    """

    # Emotion → Color palette mapping (deterministic hex codes)
    COLOR_PALETTES = {
        "joy": {
            "primary": "#FFE4B5",      # Warm yellow/peach
            "secondary": "#FFB347",    # Golden orange
            "highlight": "#FFD700",    # Gold
            "shadow": "#DEB887",       # Burlywood
        },
        "sadness": {
            "primary": "#B0C4DE",      # Light steel blue
            "secondary": "#778899",    # Light slate gray
            "highlight": "#E6E6FA",    # Lavender
            "shadow": "#6B8E23",       # Olive drab (muted)
        },
        "anger": {
            "primary": "#DC143C",      # Crimson red
            "secondary": "#8B0000",    # Dark red
            "highlight": "#FF4500",    # Orange red
            "shadow": "#2F4F4F",       # Dark slate gray
        },
        "surprise": {
            "primary": "#98FB98",      # Pale green
            "secondary": "#87CEEB",    # Sky blue
            "highlight": "#FFFFFF",    # White (sparkle)
            "shadow": "#4682B4",       # Steel blue
        },
        "fear": {
            "primary": "#D3D3D3",      # Light gray
            "secondary": "#A9A9A9",    # Dark gray
            "highlight": "#F5F5DC",    # Beige
            "shadow": "#556B2F",       # Dark olive green
        },
        "disgust": {
            "primary": "#8FBC8F",      # Dark sea green
            "secondary": "#6B8E23",    # Olive drab
            "highlight": "#9ACD32",    # Yellow green
            "shadow": "#556B2F",       # Dark olive green
        },
        "neutral": {
            "primary": "#DEB887",      # Burlywood (natural)
            "secondary": "#CD853F",    # Peru
            "highlight": "#FFE4C4",    # Bisque
            "shadow": "#8B7355",       # Dark tan
        },
    }

    # Emotion → Eye features mapping
    EYE_FEATURES = {
        "joy": {"brightness": 1.3, "size": 1.15, "sharpness": 1.1, "pupil": 0.9, "highlight": 1.5},
        "sadness": {"brightness": 0.8, "size": 0.95, "sharpness": 0.9, "pupil": 1.1, "highlight": 0.7},
        "anger": {"brightness": 1.1, "size": 1.05, "sharpness": 1.4, "pupil": 0.8, "highlight": 1.2},
        "surprise": {"brightness": 1.4, "size": 1.3, "sharpness": 1.2, "pupil": 0.85, "highlight": 1.8},
        "fear": {"brightness": 1.0, "size": 1.1, "sharpness": 1.0, "pupil": 1.3, "highlight": 1.1},
        "disgust": {"brightness": 0.9, "size": 1.0, "sharpness": 0.95, "pupil": 0.95, "highlight": 0.9},
        "neutral": {"brightness": 1.0, "size": 1.0, "sharpness": 1.0, "pupil": 1.0, "highlight": 1.0},
    }

    # Emotion → Mouth features mapping
    MOUTH_FEATURES = {
        "joy": {"curvature": 0.8, "openness": 0.2, "width": 1.2, "tension": 0.0},
        "sadness": {"curvature": -0.6, "openness": 0.1, "width": 0.9, "tension": 0.1},
        "anger": {"curvature": -0.2, "openness": 0.3, "width": 1.0, "tension": 0.8},
        "surprise": {"curvature": 0.0, "openness": 0.7, "width": 1.1, "tension": 0.2},
        "fear": {"curvature": -0.3, "openness": 0.5, "width": 0.95, "tension": 0.4},
        "disgust": {"curvature": -0.4, "openness": 0.2, "width": 0.95, "tension": 0.6},
        "neutral": {"curvature": 0.05, "openness": 0.05, "width": 1.0, "tension": 0.0},
    }

    # Emotion → Skin warmth modifier
    SKIN_WARMTH = {
        "joy": 1.3,
        "sadness": 0.8,
        "anger": 1.1,
        "surprise": 1.0,
        "fear": 0.85,
        "disgust": 0.9,
        "neutral": 1.0,
    }

    # Special effects per emotion
    SPECIAL_EFFECTS = {
        "joy": ["soft_glow", "sparkle_highlights"],
        "sadness": ["tear_trail", "subtle_blur"],
        "anger": ["sharp_edges", "heat_haze", "pulse_red"],
        "surprise": ["star_glint", "eye_expand"],
        "fear": ["tremble", "shadow_edges"],
        "disgust": ["green_tint", "warp_subtle"],
        "neutral": [],
    }

    def generate_visual_state(
        self,
        emotion: str,
        intensity: float = 0.5,
        text_context: Optional[str] = None
    ) -> Dict:
        """
        Generate complete visual identity state from emotion.
        All transformations are deterministic based on emotion and intensity.
        """
        # Normalize emotion to known value
        if emotion not in self.COLOR_PALETTES:
            emotion = "neutral"

        # Get base color palette
        palette = self.COLOR_PALETTES[emotion]

        # Intensity modifies effect strength
        intensity_factor = intensity

        # Apply eye features with intensity modulation
        eye_base = self.EYE_FEATURES[emotion]
        eye_features = EyeFeatures(
            brightness=eye_base["brightness"] * (0.7 + 0.3 * intensity_factor),
            size_multiplier=eye_base["size"] if intensity < 0.8 else eye_base["size"] * (1 + 0.3 * intensity_factor),
            sharpness=eye_base["sharpness"],
            pupil_dilation=eye_base["pupil"],
            highlight_intensity=eye_base["highlight"] * intensity_factor,
        )

        # Apply mouth features
        mouth_base = self.MOUTH_FEATURES[emotion]
        mouth_features = MouthFeatures(
            curvature=mouth_base["curvature"] * intensity_factor,
            openness=mouth_base["openness"] * intensity_factor,
            width=mouth_base["width"] if intensity < 0.9 else mouth_base["width"] * (1 + 0.2 * intensity_factor),
            tension=mouth_base["tension"] * intensity_factor,
        )

        # Skin warmth modulated by intensity
        skin_warmth = self.SKIN_WARMTH[emotion] * (0.8 + 0.2 * intensity_factor)

        # Special effects only at higher intensity
        special_effects = []
        if intensity >= 0.5:
            special_effects = self.SPECIAL_EFFECTS.get(emotion, []).copy()

        # Build visual state dict
        visual_state = VisualState(
            emotion=emotion,
            intensity=intensity,
            color_palette=ColorPalette(**palette),
            eye_features=eye_features,
            mouth_features=mouth_features,
            skin_tone=SkinTone(warmth=skin_warmth),
            special_effects=special_effects,
            metadata={
                "roughness": 0.3 if emotion in ["joy", "surprise"] else 0.6,
                "metalness": 0.0,  # anime style: non-metallic
                "subsurface_scatter": 0.2 if emotion in ["sadness", "fear"] else 0.1,
            }
        )

        return visual_state.model_dump()


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEUROTWIN Visual Identity Engine",
    description="Deterministic styling engine for avatar appearance based on emotion",
    version="1.0.0",
)
app.add_middleware(TraceMiddleware)

engine = VisualIdentityEngine()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "visual-identity",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/v1/style/emotion", response_model=AvatarStyleResponse)
async def style_from_emotion(input_data: EmotionInput):
    """
    Receive emotion from perception service and return visual styling parameters.
    This is the main entry point for converting emotional state to avatar appearance.
    """
    try:
        visual_state_dict = engine.generate_visual_state(
            emotion=input_data.emotion,
            intensity=input_data.intensity,
            text_context=input_data.text_context
        )

        visual_state = VisualState(**visual_state_dict)

        # Generate description for debugging/UI
        descriptions = {
            "joy": "Warm, bright appearance with golden tones and sparkling eyes",
            "sadness": "Cool, muted palette with soft, lowered gaze",
            "anger": "Sharp, high-contrast red tones with intense focused eyes",
            "surprise": "Vibrant colors with wide, bright eyes and open mouth",
            "fear": "Gray, muted tones with dilated pupils and cautious expression",
            "disgust": "Green-tinged palette with narrowed, turned expression",
            "neutral": "Natural, balanced appearance with standard colors",
        }

        response = AvatarStyleResponse(
            visual_state=visual_state,
            expression_override=None,  # let avatar service handle expression
            blend_time_ms=300,
            description=descriptions.get(input_data.emotion, "Custom visual state")
        )

        logger.info(
            f"Generated visual style: emotion={input_data.emotion}, intensity={input_data.intensity:.2f}"
        )
        return response

    except Exception as e:
        logger.error(f"Visual styling failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/style/enrich-avatar-command")
async def enrich_avatar_command(
    emotion: str,
    intensity: float = 0.5,
    base_avatar_command: Optional[Dict] = None
):
    """
    Take an existing avatar command and enrich it with visual identity parameters.
    This allows the conversation service to continue using its avatar_command format
    while enhanced visual styling is added as a separate layer.
    """
    style_response = await style_from_emotion(
        EmotionInput(emotion=emotion, intensity=intensity)
    )

    # Merge visual identity into avatar command if provided
    if base_avatar_command:
        enriched = base_avatar_command.copy()
        enriched["visual_identity"] = style_response.visual_state.model_dump()
        return enriched
    else:
        return {
            "avatar_command": None,
            "visual_identity": style_response.visual_state.model_dump(),
            "blend_time_ms": style_response.blend_time_ms
        }


@app.get("/v1/style/palette/{emotion}")
async def get_palette_for_emotion(emotion: str, intensity: float = 0.5):
    """
    Quick endpoint to retrieve just the color palette for a given emotion.
    Useful for theming or UI elements.
    """
    emotion = emotion.lower()
    if emotion not in engine.COLOR_PALETTES:
        raise HTTPException(status_code=400, detail=f"Unknown emotion: {emotion}")

    palette = engine.COLOR_PALETTES[emotion]
    return {
        "emotion": emotion,
        "intensity": intensity,
        "palette": palette,
        "warmth_multiplier": engine.SKIN_WARMTH.get(emotion, 1.0) * (0.8 + 0.2 * intensity)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8005, reload=True)
