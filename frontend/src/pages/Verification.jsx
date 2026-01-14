import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Divider,
  Paper,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  LinearProgress
} from '@mui/material';
import { useState, useRef, useEffect } from 'react';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import api from '../services/api';

const Verification = () => {
  const [fileId, setFileId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef();

  const hasKey = (obj, key) => !!obj && Object.prototype.hasOwnProperty.call(obj, key);
  const displayValue = (v) => (v === undefined || v === null || v === '' ? '—' : String(v));

  const clamp01 = (n) => {
    const x = Number(n);
    if (Number.isNaN(x)) return 0;
    return Math.max(0, Math.min(1, x));
  };

  const scoreLabel = (score01) => {
    const s = clamp01(score01);
    if (s >= 0.9) return 'Excellent';
    if (s >= 0.75) return 'Strong';
    if (s >= 0.6) return 'Moderate';
    if (s >= 0.4) return 'Weak';
    return 'Very weak';
  };

  const scoreColor = (score01) => {
    const s = clamp01(score01);
    if (s >= 0.75) return 'success';
    if (s >= 0.5) return 'warning';
    return 'error';
  };

  const ScoreGauge = ({ label, score, subtitle, helperText }) => {
    const s = clamp01(score);
    const targetPct = Math.round(s * 100);
    const [pct, setPct] = useState(0);

    useEffect(() => {
      let raf = 0;
      const start = performance.now();
      const from = 0;
      const to = targetPct;
      const durationMs = 650;

      const tick = (now) => {
        const t = Math.min(1, (now - start) / durationMs);
        const eased = 1 - Math.pow(1 - t, 3);
        setPct(Math.round(from + (to - from) * eased));
        if (t < 1) raf = requestAnimationFrame(tick);
      };

      raf = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(raf);
    }, [targetPct]);

    const color = scoreColor(s);
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ position: 'relative', display: 'inline-flex' }}>
            <CircularProgress
              variant="determinate"
              value={100}
              sx={{ color: 'action.disabledBackground' }}
              size={88}
              thickness={5}
            />
            <CircularProgress
              variant="determinate"
              value={pct}
              color={color}
              size={88}
              thickness={5}
              sx={{ position: 'absolute', left: 0, top: 0 }}
            />
            <Box
              sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Typography variant="h6" component="div">{pct}%</Typography>
            </Box>
          </Box>

          <Box sx={{ minWidth: 240 }}>
            <Typography variant="subtitle2">{label}</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 0.5, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip size="small" color={color} label={scoreLabel(s)} />
              {typeof subtitle === 'string' && subtitle.trim() && (
                <Typography variant="body2" color="text.secondary">{subtitle}</Typography>
              )}
            </Stack>
          </Box>
        </Box>

        {helperText ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75 }}>
            {helperText}
          </Typography>
        ) : null}
      </Box>
    );
  };

  const ScoreBar = ({ label, score, hint, hidePercent = false }) => {
    const s = clamp01(score);
    const pct = Math.round(s * 100);
    const color = scoreColor(s);
    return (
      <Box sx={{ mt: 1.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
          <Typography variant="body2">{label}</Typography>
          {!hidePercent ? (
            <Typography variant="body2" color="text.secondary">{pct}%</Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">{scoreLabel(s)}</Typography>
          )}
        </Box>
        <LinearProgress variant="determinate" value={pct} color={color} sx={{ mt: 0.75, height: 8, borderRadius: 999 }} />
        {hint ? (
          <Typography variant="caption" color="text.secondary">{hint}</Typography>
        ) : null}
      </Box>
    );
  };

  const renderAiSimilarity = (res) => {
    const score = res?.ai_text_similarity_score;
    if (typeof score !== 'number') return null;

    // This score is often near-zero because we compare OCR text to *user-entered metadata*.
    // Many PDFs don't contain those metadata words in their visible content.
    // Showing 1–2% as a meter looks like a bug, so we only show the bar when it's meaningful.
    if (score < 0.1) {
      return (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
          OCR/AI check: the document text does not appear to contain the stored metadata phrases (common for many PDFs).
        </Typography>
      );
    }

    return (
      <ScoreBar
        label="OCR/AI Metadata Similarity"
        score={score}
        hint="Heuristic: checks whether the visible document text contains your stored metadata words."
      />
    );
  };

  const handleVerify = async () => {
    setError('');
    setResult(null);

    if (!fileId && !selectedFile) {
      setError('Please provide a watermark ID or upload a file.');
      return;
    }

    setLoading(true);
    try {
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const res = await api.post('/verify', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setResult(res.data);
      } else {
        const res = await api.get(`/verify/${encodeURIComponent(fileId.trim())}`);
        setResult(res.data);
      }
    } catch (err) {
      const msg =
        err.code === 'ECONNABORTED'
          ? 'Verification timed out. Please try again.'
          : err.response?.data?.detail ||
            err.response?.data?.message ||
            err.message ||
            'Verification failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setFileId('');
    setResult(null);
    setError('');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setSelectedFile(file);
      setFileId('');
      setResult(null);
      setError('');
    }
  };

  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Verify Digital Ownership
      </Typography>
      <Typography variant="body2" sx={{ mb: 2 }} color="text.secondary">
        Paste a Watermark ID or upload a file to verify authenticity.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ID Input */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          label="Watermark ID"
          variant="outlined"
          value={fileId}
          onChange={(e) => setFileId(e.target.value)}
          fullWidth
        />
      </Box>

      {/* Drag-and-drop upload */}
      <Box
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        sx={{
          border: '2px dashed',
          borderColor: 'divider',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          mb: 2,
          backgroundColor: 'background.default',
          cursor: 'pointer'
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <CloudUploadIcon fontSize="large" color="action" />
        <Typography variant="body2" color="text.secondary">
          Drag & drop your file here or click to upload
        </Typography>
        <input
          type="file"
          hidden
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*,application/pdf,video/*"
        />
      </Box>

      {selectedFile && (
        <Typography variant="body2" sx={{ mb: 2 }}>
          Selected File: <strong>{selectedFile.name}</strong>
        </Typography>
      )}

      <Button variant="contained" onClick={handleVerify} sx={{ mb: 3 }}>
        {loading ? 'Verifying...' : 'Start Verification'}
      </Button>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
          <CircularProgress size={28} />
        </Box>
      )}

      {/* Result display */}
      {result && (
        <Paper sx={{ p: 3, mt: 2 }} elevation={3}>
          <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
            {result.method && <Chip size="small" label={`Method: ${result.method}`} />}
            {typeof result.tamper_suspected === 'boolean' && (
              <Chip
                size="small"
                color={result.tamper_suspected ? 'warning' : 'success'}
                label={result.tamper_suspected ? 'Tamper suspected' : 'No tamper signals'}
              />
            )}
            {result.signature_valid === true && <Chip size="small" color="success" label="Signature valid" />}
          </Stack>

          {result.valid ? (
            <>
              <Typography variant="h6" color="success.main" gutterBottom>
                Ownership Verified
              </Typography>
              <ScoreGauge
                label={result.method === 'pades' ? 'Authoritative Signature Confidence' : 'Watermark Confidence'}
                score={typeof result.confidence === 'number' ? result.confidence : 1}
                subtitle={result.method === 'pades' ? 'PAdES validated' : 'Watermark extracted'}
                helperText={
                  result.method === 'pades'
                    ? 'Cryptographic signature validation. This is the authoritative path.'
                    : 'Confidence of watermark extraction from the uploaded file.'
                }
              />

              {renderAiSimilarity(result)}

              {typeof result.tamper_suspected === 'boolean' && (
                <Typography><b>Tamper suspected:</b> {result.tamper_suspected ? 'Yes' : 'No'}</Typography>
              )}
              {result.watermark_code && <Typography><b>Watermark Code:</b> {result.watermark_code}</Typography>}
              {result.watermark_id && <Typography><b>Watermark ID:</b> {result.watermark_id}</Typography>}
              {(result.owner?.name || result.owner?.email) && (
                <Typography>
                  <b>Owner:</b> {result.owner?.name ? `${result.owner.name} ` : ''}{result.owner?.email ? `<${result.owner.email}>` : ''}
                </Typography>
              )}
              {result.metadata?.author && <Typography><b>Author (metadata):</b> {result.metadata.author}</Typography>}
              {result.metadata?.title && <Typography><b>Title (metadata):</b> {result.metadata.title}</Typography>}
              {hasKey(result.metadata, 'organization') && (
                <Typography><b>Organization (metadata):</b> {displayValue(result.metadata.organization)}</Typography>
              )}
              {result.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.metadata.createdDate}</Typography>}
              {result.issued_at && <Typography><b>Issued:</b> {new Date(result.issued_at).toLocaleString()}</Typography>}
              {result.note && (
                <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                  {result.note}
                </Typography>
              )}
            </>
          ) : (result.method === 'perceptual_pdf' && (result.owner?.name || result.owner?.email)) ? (
            <>
              <Typography variant="h6" color="warning.main" gutterBottom>
                Ownership Match (Not Authoritative)
              </Typography>

              {typeof result.ownership_confidence === 'number' && (
                <ScoreGauge
                  label="Perceptual Ownership Confidence"
                  score={result.ownership_confidence}
                  subtitle="Per-page visual similarity"
                  helperText="Visual similarity across rendered pages. Useful for matches, but not a cryptographic proof."
                />
              )}

              {renderAiSimilarity(result)}

              {typeof result.tamper_suspected === 'boolean' && (
                <Typography><b>Tamper suspected:</b> {result.tamper_suspected ? 'Yes' : 'No'}</Typography>
              )}
              {result.watermark_code && <Typography><b>Watermark Code:</b> {result.watermark_code}</Typography>}
              {result.watermark_id && <Typography><b>Watermark ID:</b> {result.watermark_id}</Typography>}
              {(result.owner?.name || result.owner?.email) && (
                <Typography>
                  <b>Owner:</b> {result.owner?.name ? `${result.owner.name} ` : ''}{result.owner?.email ? `<${result.owner.email}>` : ''}
                </Typography>
              )}
              {result.metadata?.author && <Typography><b>Author (metadata):</b> {result.metadata.author}</Typography>}
              {result.metadata?.title && <Typography><b>Title (metadata):</b> {result.metadata.title}</Typography>}
              {hasKey(result.metadata, 'organization') && (
                <Typography><b>Organization (metadata):</b> {displayValue(result.metadata.organization)}</Typography>
              )}
              {result.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.metadata.createdDate}</Typography>}
              {result.issued_at && <Typography><b>Issued:</b> {new Date(result.issued_at).toLocaleString()}</Typography>}
              {result.note && (
                <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                  {result.note}
                </Typography>
              )}
            </>
          ) : (result.method === 'perceptual_pdf_ambiguous' && Array.isArray(result.candidates) && result.candidates.length > 0) ? (
            <>
              <Typography variant="h6" color="warning.main" gutterBottom>
                Possible Matches (Not Authoritative)
              </Typography>

              {typeof result.ownership_confidence === 'number' && (
                <ScoreGauge
                  label="Perceptual Match Strength"
                  score={result.ownership_confidence}
                  subtitle="Multiple candidates tied"
                  helperText="The file visually matches more than one record equally well (common when pages are very similar or very short)."
                />
              )}

              <Box sx={{ mt: 2 }}>
                {result.candidates.slice(0, 5).map((c, idx) => (
                  <Box key={`${c.watermark_id || c.watermark_code || idx}`} sx={{ mb: 1.25 }}>
                    <Typography variant="body2">
                      <b>Candidate {idx + 1}:</b> {c.watermark_code || '—'}
                      {c.owner?.name || c.owner?.email ? (
                        <> — {c.owner?.name ? `${c.owner.name} ` : ''}{c.owner?.email ? `<${c.owner.email}>` : ''}</>
                      ) : null}
                    </Typography>
                    {(typeof c.score === 'number' || typeof c.dist_score === 'number') && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        Score: {typeof c.score === 'number' ? `${(c.score * 100).toFixed(1)}%` : '—'}
                        {typeof c.dist_score === 'number' ? ` • Distance score: ${(c.dist_score * 100).toFixed(1)}%` : ''}
                      </Typography>
                    )}
                  </Box>
                ))}
              </Box>

              {result.note && (
                <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                  {result.note}
                </Typography>
              )}
            </>
          ) : (
            <>
              <Typography variant="h6" color="error" gutterBottom>
                Verification failed
              </Typography>
              <Typography color="text.secondary">
                {result.reason || 'No watermark found or file is tampered.'}
              </Typography>

              {result.fallback?.match && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="warning">
                    Watermark could not be decoded, but a possible match was found via perceptual similarity.
                    (dHash distance: {result.fallback.hamming_distance})
                  </Alert>

                  {typeof result.fallback.hamming_distance === 'number' && (
                    <ScoreBar
                      label="Perceptual Similarity"
                      score={1 - Math.min(64, Math.max(0, result.fallback.hamming_distance)) / 64}
                      hint="Derived from dHash distance (lower distance = higher similarity)."
                      hidePercent
                    />
                  )}

                  {result.fallback.note && (
                    <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                      {result.fallback.note}
                    </Typography>
                  )}
                  {result.fallback.owner?.name || result.fallback.owner?.email ? (
                    <Typography sx={{ mt: 1 }}>
                      <b>Owner:</b> {result.fallback.owner?.name ? `${result.fallback.owner.name} ` : ''}
                      {result.fallback.owner?.email ? `<${result.fallback.owner.email}>` : ''}
                    </Typography>
                  ) : null}
                  {result.fallback.metadata?.author && <Typography><b>Author (metadata):</b> {result.fallback.metadata.author}</Typography>}
                  {result.fallback.metadata?.title && <Typography><b>Title (metadata):</b> {result.fallback.metadata.title}</Typography>}
                  {hasKey(result.fallback.metadata, 'organization') && (
                    <Typography><b>Organization (metadata):</b> {displayValue(result.fallback.metadata.organization)}</Typography>
                  )}
                  {result.fallback.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.fallback.metadata.createdDate}</Typography>}
                  {result.fallback.issued_at && <Typography><b>Issued:</b> {new Date(result.fallback.issued_at).toLocaleString()}</Typography>}
                </Box>
              )}
            </>
          )}
        </Paper>
      )}

      <Divider sx={{ my: 4 }}>Why Verification?</Divider>
      <Typography variant="body2" color="text.secondary">
        Verification ensures your file hasn’t been tampered with and confirms the embedded watermark ID.
        SnappyTrace uses both visible and invisible watermarking techniques powered by AI to prove authenticity.
      </Typography>
    </Container>
  );
};

export default Verification;
