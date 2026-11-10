import Link from "next/link";

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`flex items-center gap-2.5 font-display text-xl font-semibold tracking-tight ${className}`}
    >
      <svg viewBox="0 0 96 96" aria-hidden="true" className="h-[26px] w-[26px] text-accent">
        <path
          fill="currentColor"
          fillRule="evenodd"
          d="M22 24h52a12 12 0 0 1 12 12v40H10V36a12 12 0 0 1 12-12Zm-4 52V56a20 20 0 0 1 40 0v20H18Z"
        />
      </svg>
      <span>
        LetMeGet<span className="text-accent">In</span>
      </span>
    </Link>
  );
}
