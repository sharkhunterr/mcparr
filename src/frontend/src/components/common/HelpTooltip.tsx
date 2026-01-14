import { useState, useRef, useEffect } from 'react';
import type { FC, ReactNode } from 'react';
import { HelpCircle, X } from 'lucide-react';

interface HelpSection {
  title: string;
  content: string | ReactNode;
}

interface HelpTooltipProps {
  /** Unique key for the help content (used for i18n) */
  helpKey?: string;
  /** Title of the help modal */
  title: string;
  /** Sections of help content */
  sections: HelpSection[];
  /** Optional custom trigger element */
  trigger?: ReactNode;
  /** Size of the help icon */
  iconSize?: 'sm' | 'md' | 'lg';
}

const ICON_SIZES = {
  sm: 'w-3.5 h-3.5',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

/**
 * A reusable help tooltip component that shows a modal with help content.
 * Can be used throughout the application for contextual help.
 *
 * @example
 * <HelpTooltip
 *   title="How Tool Chains Work"
 *   sections={[
 *     { title: "Overview", content: "Tool chains allow..." },
 *     { title: "Conditions", content: "You can define conditions..." }
 *   ]}
 * />
 */
const HelpTooltip: FC<HelpTooltipProps> = ({
  title,
  sections,
  trigger,
  iconSize = 'md',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  return (
    <>
      {/* Trigger button */}
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center justify-center p-1 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-full transition-colors"
        title={title}
        aria-label={`Help: ${title}`}
        aria-expanded={isOpen}
      >
        {trigger || <HelpCircle className={ICON_SIZES[iconSize]} />}
      </button>

      {/* Modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/10 dark:bg-black/30 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel - Full width on mobile, fixed size on desktop */}
          <div
            ref={modalRef}
            className="fixed z-50 bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col animate-slide-up
              inset-x-2 bottom-2 max-h-[60vh] rounded-lg
              sm:inset-auto sm:bottom-4 sm:right-4 sm:w-[360px] sm:max-h-[50vh]"
            role="dialog"
            aria-modal="true"
            aria-labelledby="help-title"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
              <div className="flex items-center gap-2 text-gray-700 dark:text-gray-200">
                <HelpCircle className="w-4 h-4 text-blue-500" />
                <h3 id="help-title" className="font-medium text-sm">{title}</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                aria-label="Close help"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="p-3 overflow-y-auto flex-1 space-y-2.5">
              {sections.map((section, index) => (
                <div key={index} className="space-y-1">
                  <h4 className="font-medium text-xs text-gray-800 dark:text-gray-200 flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-blue-500 flex-shrink-0" />
                    {section.title}
                  </h4>
                  <div className="text-xs text-gray-600 dark:text-gray-400 pl-2.5 leading-relaxed">
                    {typeof section.content === 'string' ? (
                      <p className="whitespace-pre-line">{section.content}</p>
                    ) : (
                      section.content
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Animation styles */}
      <style>{`
        @keyframes slide-up {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-slide-up {
          animation: slide-up 0.15s ease-out;
        }
      `}</style>
    </>
  );
};

export default HelpTooltip;
