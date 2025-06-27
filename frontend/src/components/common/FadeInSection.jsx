// src/components/common/FadeInSection.jsx
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

const FadeInSection = ({ children, delay = 0, yOffset = 30 }) => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '0px 0px -20% 0px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: yOffset }}
      animate={inView ? { opacity: 1, y: 0 } : {}} // don't animate until in view
      transition={{ duration: 0.6, ease: 'easeOut', delay }}
      style={{ willChange: 'opacity, transform' }} // helps performance
    >
      {children}
    </motion.div>
  );
};

export default FadeInSection;
