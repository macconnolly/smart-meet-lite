import email
from email.header import decode_header
import logging

logger = logging.getLogger(__name__)

class EMLParser:
    """A simple parser for .eml files."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        try:
            with open(self.file_path, 'rb') as f:
                self.msg = email.message_from_bytes(f.read())
        except FileNotFoundError:
            logger.error(f"EML file not found at: {self.file_path}")
            self.msg = None
        except Exception as e:
            logger.error(f"Error parsing EML file {self.file_path}: {e}")
            self.msg = None

    def get_header(self, header_name: str) -> str:
        """Get a header value, decoding it if necessary."""
        if not self.msg:
            return ""
        
        header_value = self.msg.get(header_name)
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            header_parts = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    header_parts.append(part.decode(charset or 'utf-8'))
                else:
                    header_parts.append(part)
            return "".join(header_parts)
        except Exception as e:
            logger.warning(f"Could not decode header '{header_name}': {e}")
            return header_value

    def get_body(self) -> str:
        """Get the text body of the email."""
        if not self.msg:
            return ""

        if self.msg.is_multipart():
            for part in self.msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))

                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    try:
                        return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                    except Exception as e:
                        logger.warning(f"Could not decode email body part: {e}")
                        return ""
        else:
            try:
                return self.msg.get_payload(decode=True).decode(self.msg.get_content_charset() or 'utf-8')
            except Exception as e:
                logger.warning(f"Could not decode email body: {e}")
                return ""
        return ""

    def get_message_id(self) -> str:
        """Get the Message-ID header."""
        return self.get_header('Message-ID').strip('<>')
