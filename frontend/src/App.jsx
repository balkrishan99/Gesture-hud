import React, { useEffect, useRef, useState } from 'react';
import { initializeHandLandmarker, detectHands } from './utils/mediapipe';

const COLORS = [
  { id: 'cyan', hex: '#06b6d4' },
  { id: 'pink', hex: '#ec4899' },
  { id: 'green', hex: '#22c55e' },
  { id: 'coral', hex: '#f43f5e' }
];

function App() {
  const videoRef = useRef(null);
  const drawingCanvasRef = useRef(null);
  const wireframeCanvasRef = useRef(null);
  
  const [isLoaded, setIsLoaded] = useState(false);
  const [activeColor, setActiveColor] = useState(COLORS[1].hex);
  const [status, setStatus] = useState('INITIALIZING');
  const [logs, setLogs] = useState(['System booted...', 'Waiting for camera...']);
  
  const lastDrawingPoint = useRef(null);
  const drawingColorRef = useRef(activeColor);

  useEffect(() => {
    drawingColorRef.current = activeColor;
  }, [activeColor]);

  useEffect(() => {
    let animationFrameId;
    let lastVideoTime = -1;

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadeddata = () => {
            addLog('Camera connected.');
            initMediaPipe();
          };
        }
      } catch (err) {
        addLog(`Camera error: ${err.message}`);
        setStatus('ERROR');
      }
    };

    const initMediaPipe = async () => {
      try {
        await initializeHandLandmarker();
        setIsLoaded(true);
        setStatus('WAITING');
        addLog('AI Vision Model loaded.');
        renderLoop();
      } catch (err) {
        addLog(`Model error: ${err.message}`);
        setStatus('ERROR');
      }
    };

    const addLog = (msg) => {
      setLogs(prev => {
        const newLogs = [...prev, msg];
        if (newLogs.length > 8) newLogs.shift();
        return newLogs;
      });
    };

    const drawLine = (ctx, start, end, color) => {
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      ctx.stroke();
    };

    const renderLoop = () => {
      if (!videoRef.current || !drawingCanvasRef.current || !wireframeCanvasRef.current) return;
      
      const video = videoRef.current;
      const wireCanvas = wireframeCanvasRef.current;
      const wireCtx = wireCanvas.getContext('2d');
      const drawCanvas = drawingCanvasRef.current;
      const drawCtx = drawCanvas.getContext('2d');

      // Match canvas size to video
      if (wireCanvas.width !== video.videoWidth) {
        wireCanvas.width = video.videoWidth;
        wireCanvas.height = video.videoHeight;
        drawCanvas.width = video.videoWidth;
        drawCanvas.height = video.videoHeight;
      }

      if (video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        
        const results = detectHands(video, performance.now());
        
        // Clear wireframe canvas every frame
        wireCtx.clearRect(0, 0, wireCanvas.width, wireCanvas.height);
        
        if (results && results.landmarks && results.landmarks.length > 0) {
          const landmarks = results.landmarks[0];
          
          // Draw Hand Wireframe (Neon Cyan)
          wireCtx.strokeStyle = '#06b6d4';
          wireCtx.lineWidth = 2;
          wireCtx.shadowColor = '#06b6d4';
          wireCtx.shadowBlur = 5;
          
          // Simple lines between points for demonstration
          for (let i = 0; i < landmarks.length - 1; i++) {
            wireCtx.beginPath();
            wireCtx.moveTo(landmarks[i].x * wireCanvas.width, landmarks[i].y * wireCanvas.height);
            wireCtx.lineTo(landmarks[i+1].x * wireCanvas.width, landmarks[i+1].y * wireCanvas.height);
            wireCtx.stroke();
          }

          // Index finger tip is landmark 8
          const indexTip = landmarks[8];
          // Middle finger tip is landmark 12
          const middleTip = landmarks[12];
          
          // Logic: Draw if index is up and middle is down (simple heuristic)
          const isDrawing = indexTip.y < landmarks[6].y && middleTip.y > landmarks[10].y;
          
          const currentPoint = {
            x: indexTip.x * drawCanvas.width,
            y: indexTip.y * drawCanvas.height
          };
          
          // Highlight index tip
          wireCtx.beginPath();
          wireCtx.arc(currentPoint.x, currentPoint.y, 6, 0, 2 * Math.PI);
          wireCtx.fillStyle = '#ec4899';
          wireCtx.fill();

          if (isDrawing) {
            if (status !== 'DRAWING') setStatus('DRAWING');
            if (lastDrawingPoint.current) {
              drawLine(drawCtx, lastDrawingPoint.current, currentPoint, drawingColorRef.current);
            }
            lastDrawingPoint.current = currentPoint;
          } else {
            if (status !== 'WAITING') setStatus('WAITING');
            lastDrawingPoint.current = null;
          }
        } else {
          if (status !== 'WAITING') setStatus('WAITING');
          lastDrawingPoint.current = null;
        }
      }
      
      animationFrameId = requestAnimationFrame(renderLoop);
    };

    startCamera();

    return () => {
      cancelAnimationFrame(animationFrameId);
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const clearCanvas = () => {
    const canvas = drawingCanvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  return (
    <div className="hud-container">
      <video ref={videoRef} autoPlay playsInline muted className="mirrored" />
      {/* Drawing canvas persists strokes */}
      <canvas ref={drawingCanvasRef} className="mirrored" />
      {/* Wireframe canvas clears every frame */}
      <canvas ref={wireframeCanvasRef} className="mirrored" />
      
      {/* HUD Elements */}
      <div className="hud-box hud-top-left">
        <div className="hud-text-label">System State</div>
        <div className="hud-text-value" style={{ color: status === 'DRAWING' ? 'var(--neon-pink)' : '#fff' }}>
          {status}
        </div>
      </div>
      
      <div className="hud-box hud-top-right">
        <div className="hud-text-label">Active Mode</div>
        <div className="hud-text-value">AIR_DRAW</div>
      </div>
      
      <div className="floating-sidebar">
        {COLORS.map(c => (
          <button
            key={c.id}
            className={`color-btn ${activeColor === c.hex ? 'active' : ''}`}
            style={{ backgroundColor: c.hex, color: c.hex }}
            onClick={() => setActiveColor(c.hex)}
            aria-label={`Select ${c.id} color`}
          />
        ))}
      </div>
      
      <button className="fab-clear" onClick={clearCanvas}>
        Clear Canvas
      </button>
      
      <div className="hud-box hud-bottom-right">
        <div className="hud-text-label">System Logs</div>
        {logs.map((log, i) => (
          <div key={i} className="log-entry">
            <span>{i + 1}.</span>
            <span>{log}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
