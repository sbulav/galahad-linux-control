use std::fs;
use std::path::Path;

const TEMP_SENSORS: &[&str] = &["coretemp", "k10temp"];

#[derive(Default)]
pub struct CpuMeter {
    last_total: Option<u64>,
    last_idle: Option<u64>,
    smoothed: Option<f32>,
}

impl CpuMeter {
    pub fn usage_percent(&mut self) -> f32 {
        let Some((total, idle)) = read_proc_stat() else {
            return self.smoothed.unwrap_or(0.0);
        };

        let current = match (self.last_total, self.last_idle) {
            (Some(last_total), Some(last_idle)) => {
                let total_delta = total.saturating_sub(last_total);
                let idle_delta = idle.saturating_sub(last_idle);
                if total_delta == 0 {
                    self.smoothed.unwrap_or(0.0)
                } else {
                    (1.0 - idle_delta as f32 / total_delta as f32) * 100.0
                }
            }
            _ => 0.0,
        };

        self.last_total = Some(total);
        self.last_idle = Some(idle);
        let smoothed = match self.smoothed {
            Some(prev) => prev * 0.7 + current * 0.3,
            None => current,
        };
        self.smoothed = Some(smoothed);
        smoothed.clamp(0.0, 100.0)
    }
}

pub fn cpu_temperature() -> Option<i32> {
    let hwmon = Path::new("/sys/class/hwmon");
    let entries = fs::read_dir(hwmon).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        let name = fs::read_to_string(path.join("name")).unwrap_or_default();
        if !TEMP_SENSORS.iter().any(|sensor| name.trim() == *sensor) {
            continue;
        }
        for idx in 1..=10 {
            let input = path.join(format!("temp{idx}_input"));
            if let Ok(value) = fs::read_to_string(input) {
                if let Ok(milli_c) = value.trim().parse::<i32>() {
                    return Some(milli_c / 1000);
                }
            }
        }
    }
    None
}

fn read_proc_stat() -> Option<(u64, u64)> {
    let stat = fs::read_to_string("/proc/stat").ok()?;
    let line = stat.lines().next()?;
    let values: Vec<u64> = line
        .split_whitespace()
        .skip(1)
        .filter_map(|value| value.parse::<u64>().ok())
        .collect();
    if values.len() < 4 {
        return None;
    }
    let idle = values[3] + values.get(4).copied().unwrap_or(0);
    let total = values.iter().sum();
    Some((total, idle))
}
