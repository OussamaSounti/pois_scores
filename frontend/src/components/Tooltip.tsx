/** "?" icon that shows score explanation on hover (native title tooltip). */
type Props = { text: string };

export default function Tooltip({ text }: Props) {
  return (
    <span
      className="tooltip-trigger"
      title={text}
      aria-label={text}
    >
      ?
    </span>
  );
}
