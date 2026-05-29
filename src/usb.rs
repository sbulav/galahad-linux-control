use crate::config::{Rgb, INTERFACE_CONTROL, PRODUCT_ID, VENDOR_ID};
use crate::protocol::{
    build_h264_packets, build_rgb_packet, SLEEP_BETWEEN_PACKETS_MS, USB_TIMEOUT_MS,
};
use anyhow::{anyhow, Context, Result};
use rusb::{DeviceHandle, Direction, GlobalContext};
use std::time::Duration;

pub struct GalahadDevice {
    handle: DeviceHandle<GlobalContext>,
    endpoint: u8,
    detached_kernel_driver: bool,
}

impl GalahadDevice {
    pub fn open() -> Result<Self> {
        let device = rusb::devices()?
            .iter()
            .find(|device| {
                device
                    .device_descriptor()
                    .map(|desc| desc.vendor_id() == VENDOR_ID && desc.product_id() == PRODUCT_ID)
                    .unwrap_or(false)
            })
            .ok_or_else(|| anyhow!("device not found"))?;

        let handle = device.open().context("failed to open USB device")?;
        let detached_kernel_driver = match handle.kernel_driver_active(INTERFACE_CONTROL) {
            Ok(true) => handle.detach_kernel_driver(INTERFACE_CONTROL).is_ok(),
            _ => false,
        };

        let _ = handle.set_active_configuration(1);
        handle
            .claim_interface(INTERFACE_CONTROL)
            .context("failed to claim USB interface; install udev rule or run as root")?;

        let config = device
            .active_config_descriptor()
            .or_else(|_| device.config_descriptor(0))?;
        let endpoint = config
            .interfaces()
            .flat_map(|iface| iface.descriptors())
            .find(|desc| desc.interface_number() == INTERFACE_CONTROL)
            .and_then(|desc| {
                desc.endpoint_descriptors()
                    .find(|endpoint| endpoint.direction() == Direction::Out)
                    .map(|endpoint| endpoint.address())
            })
            .ok_or_else(|| {
                anyhow!("failed to find OUT endpoint on interface {INTERFACE_CONTROL}")
            })?;

        Ok(Self {
            handle,
            endpoint,
            detached_kernel_driver,
        })
    }

    pub fn set_rgb_color(&mut self, rgb: Rgb) -> Result<()> {
        let packet = build_rgb_packet(rgb);
        self.handle
            .write_bulk(self.endpoint, &packet, Duration::from_millis(1000))
            .context("failed to write RGB packet")?;
        Ok(())
    }

    pub fn send_h264_frame(&mut self, h264: &[u8]) -> Result<()> {
        for packet in build_h264_packets(h264) {
            self.handle
                .write_bulk(
                    self.endpoint,
                    &packet,
                    Duration::from_millis(USB_TIMEOUT_MS),
                )
                .context("failed to write H.264 packet")?;
            std::thread::sleep(Duration::from_millis(SLEEP_BETWEEN_PACKETS_MS));
        }
        Ok(())
    }
}

impl Drop for GalahadDevice {
    fn drop(&mut self) {
        if let Err(err) = self.handle.release_interface(INTERFACE_CONTROL) {
            eprintln!("  ⚠️  Warning: Failed to release interface: {err}");
        }
        if self.detached_kernel_driver {
            if let Err(err) = self.handle.attach_kernel_driver(INTERFACE_CONTROL) {
                eprintln!("  ⚠️  Warning: Failed to re-attach kernel driver: {err}");
            }
        }
        if let Err(err) = self.handle.reset() {
            eprintln!("  ⚠️  Warning: Failed to reset device: {err}");
        }
    }
}
