pub mod app;
pub mod cli;
pub mod config;
pub mod encode;
pub mod metrics;
pub mod presets;
pub mod protocol;
pub mod render;
pub mod usb;

pub use cli::{parse_color, Args, PresetMode, ScalingMode};
pub use config::{
    effective_rgb, load_settings, load_settings_from, resolve_config_path, Colors, Rgb, Settings,
};
pub use encode::encode_h264;
pub use protocol::{build_h264_packets, build_rgb_packet};
pub use render::{create_frame, load_background};
