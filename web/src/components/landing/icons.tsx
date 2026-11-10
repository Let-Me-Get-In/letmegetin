type IconProps = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function SearchIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="11" cy="11" r="7" />
      <path d="m16.5 16.5 4.5 4.5" />
    </svg>
  );
}

export function ArrowIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 12h15" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="m20 6-11 11-5-5" />
    </svg>
  );
}

export function EntranceIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M5 21V4a1 1 0 0 1 1-1h9" />
      <path d="M15 3v18" />
      <path d="M3 21h18" />
      <path d="m19 12-3-3m3 3-3 3" />
    </svg>
  );
}

export function ToiletIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="10" cy="4" r="2" />
      <path d="M10 6v6h5l3 6" />
      <circle cx="14" cy="18" r="3.5" />
    </svg>
  );
}

export function LoopIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M6 8a5 5 0 1 1 10 0c0 4-4 4-4 7a3 3 0 0 1-6 0" />
      <path d="M16 17a5 5 0 0 1-8 3" />
    </svg>
  );
}

export function StaffIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 21a7 7 0 0 1 14 0" />
    </svg>
  );
}

export function CodeIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="m8 7-5 5 5 5" />
      <path d="m16 7 5 5-5 5" />
      <path d="m14 5-4 14" />
    </svg>
  );
}
