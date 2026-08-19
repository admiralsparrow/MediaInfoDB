import type { MediaFileDetail } from "../../types/media";

interface Props {
  detail: MediaFileDetail;
}

export default function TrackDetails({ detail }: Props) {
  return (
    <div className="track-details">
      <div className="track-section track-section-file">
        <h4>File Info <span className="track-section-filename">{detail.file_name}</span></h4>
        <div className="track-grid file-grid">
          <Detail label="Container" value={detail.container_format} />
          <Detail label="Size" value={formatFileSize(detail.file_size_bytes)} />
          <Detail label="Duration" value={formatDuration(detail.duration_ms)} />
          <Detail label="Overall Bitrate" value={formatBitrate(detail.overall_bitrate)} />
          <Detail label="Streams" value={detail.stream_count?.toString()} />
          <Detail label="Source" value={detail.source} />
          <Detail label="Provider" value={detail.provider} />
          <Detail label="Release Group" value={detail.release_group} />
          <Detail label="Year" value={detail.year?.toString()} />
          {detail.title && <Detail label="Title" value={detail.title} wide />}
        </div>
      </div>

      {detail.video_tracks.length > 0 && (
        <div className="track-section">
          <h4>Video Tracks ({detail.video_tracks.length})</h4>
          {detail.video_tracks.map((t) => (
            <div key={t.id} className="track-card">
              <div className="track-card-header">
                <span className="track-index">#{t.track_index}</span>
                <span className="track-codec">{t.codec}</span>
                {t.resolution && <span className="badge">{t.resolution}</span>}
                {t.hdr10 && <span className="badge badge-hdr">HDR10</span>}
                {t.dolby_vision && (
                  <span className="badge badge-dv">
                    DV P{t.dv_profile ?? "?"}.L{t.dv_layer ? parseInt(t.dv_layer, 10) : "?"}
                  </span>
                )}
                {t.hdr10_plus && <span className="badge badge-hdr">HDR10+</span>}
                {t.language && <span className="lang-tag">{t.language}</span>}
                {t.is_default && <span className="flag">Default</span>}
                {t.is_forced && <span className="flag">Forced</span>}
              </div>
              <div className="track-grid">
                <Detail label="Resolution" value={t.width && t.height ? `${t.width}×${t.height}` : null} />
                <Detail label="Aspect Ratio" value={t.display_aspect_ratio} />
                <Detail label="Framerate" value={t.framerate ? `${t.framerate} fps` : null} />
                <Detail label="Bitrate" value={formatBitrate(t.bitrate)} />
                <Detail label="Bit Depth" value={t.bit_depth ? `${t.bit_depth}-bit` : null} />
                <Detail label="Chroma" value={t.chroma_subsampling} />
                <Detail label="Color Primaries" value={t.color_primaries} />
                <Detail label="Transfer" value={t.transfer_characteristics} />
                <Detail label="Scan Type" value={t.scan_type} />
                <Detail label="Encoder" value={t.encoding_library} />
                {t.track_name && <Detail label="Track Name" value={t.track_name} wide />}
              </div>
            </div>
          ))}
        </div>
      )}

      {detail.audio_tracks.length > 0 && (
        <div className="track-section">
          <h4>Audio Tracks ({detail.audio_tracks.length})</h4>
          {detail.audio_tracks.map((t) => (
            <div key={t.id} className="track-card">
              <div className="track-card-header">
                <span className="track-index">#{t.track_index}</span>
                {t.language && <span className="lang-tag">{t.language}</span>}
                <span className="track-codec">{t.codec}</span>
                <span>{t.channel_layout ?? `${t.channels}ch`}</span>
                {t.is_atmos && <span className="badge badge-atmos">Atmos</span>}
                {t.is_default && <span className="flag">Default</span>}
                {t.is_original && <span className="flag">Original</span>}
                {t.is_forced && <span className="flag">Forced</span>}
                {t.is_commentary && <span className="flag">Commentary</span>}
                {t.track_name && <span className="track-name">{t.track_name}</span>}
              </div>
              <div className="track-grid">
                <Detail label="Bitrate" value={formatBitrate(t.bitrate)} />
                <Detail label="Channels" value={t.channels?.toString()} />
                <Detail label="Layout" value={t.channel_layout} />
                <Detail label="Sample Rate" value={t.sample_rate ? `${(t.sample_rate / 1000).toFixed(1)} kHz` : null} />
                <Detail label="Compression" value={t.compression_mode} />
              </div>
            </div>
          ))}
        </div>
      )}

      {detail.subtitle_tracks.length > 0 && (
        <div className="track-section">
          <h4>Subtitle Tracks ({detail.subtitle_tracks.length})</h4>
          <div className="subtitle-grid">
            {detail.subtitle_tracks.map((t) => (
              <div key={t.id} className="track-card">
                <div className="track-card-header">
                  <span className="track-index">#{t.track_index}</span>
                  <span className="track-codec">{t.codec}</span>
                  {t.language && <span className="lang-tag">{t.language}</span>}
                  {t.is_default && <span className="flag">Default</span>}
                  {t.is_forced && <span className="flag">Forced</span>}
                  {t.is_hearing_impaired && <span className="flag flag-hi">HI</span>}
                  {t.track_name && <span className="track-name">{t.track_name}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="track-section track-section-meta">
        <h4>Scan Info</h4>
        <div className="track-grid">
          <Detail label="Scanned At" value={formatDate(detail.scanned_at)} />
          <Detail label="File Path" value={detail.file_path} wide />
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, wide }: { label: string; value: string | null | undefined; wide?: boolean }) {
  if (!value) return null;
  return (
    <div className={`track-detail${wide ? " track-detail-wide" : ""}`}>
      <span className="track-detail-label">{label}</span>
      <span className="track-detail-value">{value}</span>
    </div>
  );
}

function formatBitrate(bps: number | null | undefined): string | null {
  if (!bps) return null;
  if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} Mbps`;
  if (bps >= 1_000) return `${(bps / 1_000).toFixed(0)} kbps`;
  return `${bps} bps`;
}

function formatFileSize(bytes: number | null | undefined): string | null {
  if (!bytes) return null;
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

function formatDuration(ms: number | null | undefined): string | null {
  if (!ms) return null;
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleString();
}
