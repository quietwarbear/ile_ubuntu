import React from 'react';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { GoogleLogo, Presentation, Article } from '@phosphor-icons/react';

export function GoogleImportDialog({
  importOpen, importTab, googleSlides, googleDocs, importing,
  onClose, onSetTab, onImportSlide, onImportDoc,
}) {
  return (
    <Dialog open={importOpen !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))] max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <GoogleLogo size={20} className="text-[rgb(var(--gold))]" /> Import from Google
          </DialogTitle>
        </DialogHeader>

        <div className="flex gap-1 p-1 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md mb-4">
          <button
            onClick={() => onSetTab('slides')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
              importTab === 'slides' ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))]' : 'text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))]'
            }`}
            data-testid="import-tab-slides"
          >
            <Presentation size={14} /> Slides
          </button>
          <button
            onClick={() => onSetTab('docs')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
              importTab === 'docs' ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))]' : 'text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))]'
            }`}
            data-testid="import-tab-docs"
          >
            <Article size={14} /> Docs
          </button>
        </div>

        <div className="space-y-2">
          {importTab === 'slides' && (
            googleSlides.length === 0 ? (
              <p className="text-sm text-[rgb(var(--text-muted))] text-center py-4">No Google Slides found in your account.</p>
            ) : (
              googleSlides.map(slide => (
                <div
                  key={slide.id}
                  className="flex items-center gap-3 p-3 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md hover:border-[rgb(var(--gold)/0.2)] transition-colors"
                  data-testid={`import-slide-${slide.id}`}
                >
                  <Presentation size={20} weight="duotone" className="text-[rgb(var(--gold))] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[rgb(var(--text-main))] truncate">{slide.name}</p>
                    <p className="text-[10px] text-[rgb(var(--text-muted))]">Modified {new Date(slide.modifiedTime).toLocaleDateString()}</p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => onImportSlide(slide.id, importOpen)}
                    className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-[10px]"
                    disabled={importing}
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </Button>
                </div>
              ))
            )
          )}
          {importTab === 'docs' && (
            googleDocs.length === 0 ? (
              <p className="text-sm text-[rgb(var(--text-muted))] text-center py-4">No Google Docs found in your account.</p>
            ) : (
              googleDocs.map(doc => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 p-3 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md hover:border-[rgb(var(--gold)/0.2)] transition-colors"
                  data-testid={`import-doc-${doc.id}`}
                >
                  <Article size={20} weight="duotone" className="text-[rgb(var(--gold))] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[rgb(var(--text-main))] truncate">{doc.name}</p>
                    <p className="text-[10px] text-[rgb(var(--text-muted))]">Modified {new Date(doc.modifiedTime).toLocaleDateString()}</p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => onImportDoc(doc.id, importOpen)}
                    className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-[10px]"
                    disabled={importing}
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </Button>
                </div>
              ))
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
