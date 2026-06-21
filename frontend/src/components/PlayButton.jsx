import "../styles/playbutton.css";

export function PlayButton({ playing, onToggle, disabled }) {
  return (
    <button
      className={`play-btn ${playing ? "play-btn--playing" : ""} ${disabled ? "play-btn--disabled" : ""}`}
      onClick={onToggle}
      disabled={disabled}
      title={disabled ? "Select an event first" : playing ? "Stop" : "Play collision animation"}
    >
      <span className="play-btn__icon">
        {playing ? "■" : "▶"}
      </span>
      <span className="play-btn__label">
        {disabled ? "Select event" : playing ? "Stop" : "Play collision"}
      </span>
    </button>
  );
}