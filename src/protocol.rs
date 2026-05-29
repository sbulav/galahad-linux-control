use crate::config::Rgb;

pub const H264_HEADER_1: u8 = 0x02;
pub const H264_HEADER_2: u8 = 0x0D;
pub const H264_CHUNK_SIZE: usize = 1013;
pub const H264_PACKET_SIZE: usize = 1024;
pub const USB_TIMEOUT_MS: u64 = 2000;
pub const SLEEP_BETWEEN_PACKETS_MS: u64 = 1;

pub const RGB_PACKET_SIZE: usize = 64;

pub fn build_rgb_packet(rgb: Rgb) -> [u8; RGB_PACKET_SIZE] {
    let mut packet = [0u8; RGB_PACKET_SIZE];
    packet[0] = 0x01;
    packet[1] = 0x83;
    packet[5] = 19;
    packet[6] = 0x00;
    packet[7] = 0x03;
    packet[8] = 0x04;
    packet[9] = 0x00;
    packet[10] = rgb.0;
    packet[11] = rgb.1;
    packet[12] = rgb.2;
    packet
}

pub fn build_h264_packets(h264: &[u8]) -> Vec<[u8; H264_PACKET_SIZE]> {
    let mut packets = Vec::new();
    let total_len = h264.len() as u32;

    for (seq, chunk) in h264.chunks(H264_CHUNK_SIZE).enumerate() {
        let mut packet = [0u8; H264_PACKET_SIZE];
        packet[0] = H264_HEADER_1;
        packet[1] = H264_HEADER_2;
        packet[2] = ((total_len >> 24) & 0xFF) as u8;
        packet[3] = ((total_len >> 16) & 0xFF) as u8;
        packet[4] = ((total_len >> 8) & 0xFF) as u8;
        packet[5] = (total_len & 0xFF) as u8;

        let seq = seq as u32;
        packet[6] = ((seq >> 16) & 0xFF) as u8;
        packet[7] = ((seq >> 8) & 0xFF) as u8;
        packet[8] = (seq & 0xFF) as u8;

        let chunk_len = chunk.len() as u16;
        packet[9] = ((chunk_len >> 8) & 0xFF) as u8;
        packet[10] = (chunk_len & 0xFF) as u8;
        packet[11..11 + chunk.len()].copy_from_slice(chunk);
        packets.push(packet);
    }

    packets
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_rgb_packet() {
        let packet = build_rgb_packet(Rgb(1, 2, 3));
        assert_eq!(packet.len(), 64);
        assert_eq!(&packet[0..2], &[0x01, 0x83]);
        assert_eq!(packet[5], 19);
        assert_eq!(&packet[6..13], &[0x00, 0x03, 0x04, 0x00, 1, 2, 3]);
    }

    #[test]
    fn chunks_h264_payload() {
        let data = vec![b'A'; 2500];
        let packets = build_h264_packets(&data);
        assert_eq!(packets.len(), 3);
        assert_eq!(&packets[0][0..2], &[0x02, 0x0D]);
        let total_len = ((packets[0][2] as u32) << 24)
            | ((packets[0][3] as u32) << 16)
            | ((packets[0][4] as u32) << 8)
            | packets[0][5] as u32;
        assert_eq!(total_len, 2500);
        let mut joined = Vec::new();
        for packet in packets {
            let len = ((packet[9] as usize) << 8) | packet[10] as usize;
            joined.extend_from_slice(&packet[11..11 + len]);
        }
        assert_eq!(joined, data);
    }

    #[test]
    fn empty_h264_makes_no_packets() {
        assert!(build_h264_packets(&[]).is_empty());
    }
}
