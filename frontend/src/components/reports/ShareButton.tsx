/**
 * Share Button Component
 *
 * Button that opens the share link dialog for a report.
 */

import React, { useState } from 'react';
import { useTranslation } from '../../hooks/useTranslation';
import { Button } from '../common';
import ShareLinkDialog from './ShareLinkDialog';

interface ShareButtonProps {
  reportId: string;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

const ShareButton: React.FC<ShareButtonProps> = ({ reportId, variant = 'secondary', size = 'sm' }) => {
  const { t } = useTranslation();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => setDialogOpen(true)}
      >
        <ShareIcon className="h-4 w-4 mr-2" />
        {t('share.button')}
      </Button>

      <ShareLinkDialog
        reportId={reportId}
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
};

// Share Icon
const ShareIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
    />
  </svg>
);

export default ShareButton;
